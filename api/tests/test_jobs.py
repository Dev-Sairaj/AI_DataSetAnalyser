import time
from io import BytesIO

import pandas as pd


def _upload(client, content, name="data.csv"):
    return client.post("/api/datasets", files={"file": (name, content, "text/csv")})


def _wait(client, job_id, timeout=20.0):
    deadline = time.time() + timeout
    while True:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("completed", "failed") or time.time() > deadline:
            return job
        time.sleep(0.2)


def test_upload_returns_columns(client, csv_bytes):
    response = _upload(client, csv_bytes)
    assert response.status_code == 201
    body = response.json()
    assert body["job"]["status"] == "uploaded"
    assert [c["name"] for c in body["columns"]] == ["a", "b", "y"]
    assert body["sheets"] == []


def test_rejects_unsupported_type(client):
    assert _upload(client, b"{}", "data.json").status_code == 415


def test_rejects_oversized_upload(client):
    big = b"1,2\n" * 1_700_000  # about 6.8 MB, limit in tests is 5 MB
    assert _upload(client, big).status_code == 413
    assert client.get("/api/jobs").json() == []  # nothing left behind


def test_full_flow(client, csv_bytes):
    job_id = _upload(client, csv_bytes).json()["job"]["job_id"]

    run = client.post(f"/api/jobs/{job_id}/run", json={"target": "y"})
    assert run.status_code == 202

    job = _wait(client, job_id)
    assert job["status"] == "completed", job
    assert job["progress"] == 1.0
    assert set(job["available_downloads"]) == {"html", "json", "excel", "pdf"}

    result = client.get(f"/api/jobs/{job_id}/result").json()
    assert result["profile"]["n_rows"] == 100
    assert result["target"] == "y"
    assert len(result["sop"]["stages"]) == 8
    assert len(result["quality"]["dimension_scores"]) == 6
    assert result["quality"]["grading_thresholds"]["A"] == 90
    assert (
        next(
            dimension
            for dimension in result["quality"]["dimension_scores"]
            if dimension["name"] == "Timeliness"
        )["assessment"]
        == "not_assessed"
    )

    for fmt in ("html", "json", "excel", "pdf"):
        download = client.get(f"/api/jobs/{job_id}/downloads/{fmt}")
        assert download.status_code == 200 and len(download.content) > 0
    assert client.get(f"/api/jobs/{job_id}/downloads/docx").status_code == 404
    final_dataset = client.get(f"/api/jobs/{job_id}/downloads/final-dataset")
    assert final_dataset.status_code == 200
    assert final_dataset.content == csv_bytes


def test_bad_target_fails_cleanly(client, csv_bytes):
    job_id = _upload(client, csv_bytes).json()["job"]["job_id"]
    client.post(f"/api/jobs/{job_id}/run", json={"target": "nope"})
    job = _wait(client, job_id)
    assert job["status"] == "failed"
    assert "nope" in job["error"]


def test_result_before_run_is_409(client, csv_bytes):
    job_id = _upload(client, csv_bytes).json()["job"]["job_id"]
    assert client.get(f"/api/jobs/{job_id}/result").status_code == 409


def test_unknown_and_malformed_ids_are_404(client):
    assert client.get("/api/jobs/" + "0" * 32).status_code == 404
    assert client.get("/api/jobs/not-a-real-id").status_code == 404
    assert client.get("/api/jobs/..%2F..%2Fetc/result").status_code == 404


def test_delete_job(client, csv_bytes):
    job_id = _upload(client, csv_bytes).json()["job"]["job_id"]
    assert client.delete(f"/api/jobs/{job_id}").status_code == 204
    assert client.get(f"/api/jobs/{job_id}").status_code == 404


def test_standardization_creates_separate_download(client):
    """Standardization preserves the upload and produces an audited derived CSV."""
    content = (
        b"city,event_date,phone,value,y\n"
        b" New   Delhi ,31/12/2025,98765 43210,10,0\n"
        b"MUMBAI,01/01/2026,+919123456789,20,1\n"
    )
    job_id = _upload(client, content).json()["job"]["job_id"]
    client.post(f"/api/jobs/{job_id}/run", json={"target": "y"})
    assert _wait(client, job_id)["status"] == "completed"
    pdf_before = client.get(f"/api/jobs/{job_id}/downloads/pdf").content

    response = client.post(
        f"/api/jobs/{job_id}/standardize",
        json={
            "text_columns": ["city"],
            "text_case": "lower",
            "date_columns": ["event_date"],
            "date_format": "%Y-%m-%d",
            "dayfirst": True,
            "phone_columns": ["phone"],
            "phone_country_code": "91",
            "numeric_columns": ["value", "y"],
            "scaling_method": "minmax",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["file_format"] == "csv"
    assert len(body["report"]["before"]["dimensions"]) == 6
    assert len(body["report"]["after"]["dimensions"]) == 6
    assert body["report"]["records_modified"] == 2
    assert body["report"]["records_removed"] == 0
    assert body["report"]["before"]["missing_values"] == 0
    assert body["report"]["after"]["missing_values"] == 0
    assert body["report"]["comparison_notes"]
    assert {step["fix"] for step in body["report"]["steps"]} == {
        "standardize_text",
        "normalize_dates",
        "standardize_phone",
        "scale",
    }
    assert next(step for step in body["report"]["steps"] if step["fix"] == "scale")[
        "ignored_columns"
    ] == ["y"]

    download = client.get(f"/api/jobs/{job_id}/downloads/standardized")
    assert download.status_code == 200
    output = pd.read_csv(BytesIO(download.content), dtype=str)
    assert output["city"].tolist() == ["new delhi", "mumbai"]
    assert output["event_date"].tolist() == ["2025-12-31", "2026-01-01"]
    assert output["phone"].tolist() == ["+919876543210", "+919123456789"]
    assert output["value"].astype(float).tolist() == [0.0, 1.0]
    assert output["y"].tolist() == ["0", "1"]

    final_dataset = client.get(f"/api/jobs/{job_id}/downloads/final-dataset")
    assert final_dataset.status_code == 200
    assert final_dataset.content == download.content
    pdf_after = client.get(f"/api/jobs/{job_id}/downloads/pdf").content
    assert pdf_after.startswith(b"%PDF")
    assert pdf_after != pdf_before

    source = client.app.state.jobs.storage.input_path(job_id)
    assert source.read_bytes() == content
    assert client.get(f"/api/jobs/{job_id}/standardization").status_code == 200
