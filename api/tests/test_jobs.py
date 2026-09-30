import time


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
    assert set(job["available_downloads"]) == {"html", "json", "excel"}

    result = client.get(f"/api/jobs/{job_id}/result").json()
    assert result["profile"]["n_rows"] == 100
    assert result["target"] == "y"

    for fmt in ("html", "json", "excel"):
        download = client.get(f"/api/jobs/{job_id}/downloads/{fmt}")
        assert download.status_code == 200 and len(download.content) > 0
    assert client.get(f"/api/jobs/{job_id}/downloads/pdf").status_code == 404


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