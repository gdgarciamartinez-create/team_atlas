import json
from fastapi.testclient import TestClient
from atlas.main import app

def test_smoke_snapshot():
    c = TestClient(app)
    r = c.get("/api/snapshot")
    assert r.status_code == 200
    j = r.json()
    assert "symbols" in j
    assert "exec" in j