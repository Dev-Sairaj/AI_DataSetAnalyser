def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert ".csv" in body["supported_extensions"]
    assert {"html", "json", "excel"} <= set(body["export_formats"])