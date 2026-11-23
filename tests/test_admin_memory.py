"""Kiểm tra /api/admin/memory: sai khóa thì 401, đúng khóa thì chỉ có rss_mb (số) và models_loaded."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from server import main  # noqa: E402
from sparkmind import config  # noqa: E402


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(config, "INGEST_SECRET", "bi-mat")
    return TestClient(main.app)


def test_sai_khoa_401(client):
    assert client.get("/api/admin/memory", headers={"x-api-key": "sai"}).status_code == 401
    assert client.get("/api/admin/memory").status_code == 401


def test_dung_khoa_co_rss(client):
    r = client.get("/api/admin/memory", headers={"x-api-key": "bi-mat"})
    assert r.status_code == 200
    d = r.json()
    assert set(d) == {"rss_mb", "models_loaded"}
    assert isinstance(d["rss_mb"], (int, float)) and d["rss_mb"] > 0
    assert isinstance(d["models_loaded"], bool)
