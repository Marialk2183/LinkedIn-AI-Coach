"""End-to-end API contract checks via FastAPI's TestClient."""

import io
import zipfile

import pytest
from fastapi.testclient import TestClient

import main
from ml.synthesize import ARCHETYPES


@pytest.fixture(scope="module")
def client():
    return TestClient(main.app)


def test_health_reports_model(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["ml_loaded"] is True
    assert body["model_version"] == 2
    assert "cv_r2" in body["model_metrics"]


def test_analyze_full_payload(client):
    r = client.post("/api/v1/analyze",
                    json={"source_type": "text", "profile_text": ARCHETYPES["strong"]})
    assert r.status_code == 200
    d = r.json()
    assert d["ml_used"] is True
    assert d["scores"]["overall"] >= 70
    assert d["career_predictions"]
    assert d["recommendations"]
    assert d["analysis_id"] is not None


def test_analyze_orders_tiers(client):
    def overall(tier):
        return client.post(
            "/api/v1/analyze",
            json={"source_type": "text", "profile_text": ARCHETYPES[tier]},
        ).json()["scores"]["overall"]

    assert overall("weak") < overall("average") < overall("strong") < overall("elite")


def test_analyze_requires_text(client):
    r = client.post("/api/v1/analyze", json={"source_type": "text", "profile_text": "  "})
    assert r.status_code == 422


def test_upload_text_file(client):
    r = client.post(
        "/api/v1/analyze/upload",
        files={"file": ("profile.txt", ARCHETYPES["strong"].encode(), "text/plain")},
    )
    assert r.status_code == 200
    d = r.json()
    assert d["source_type"] == "export"
    assert d["scores"]["overall"] >= 70
    assert d["recommendations"]


def test_upload_linkedin_zip(client):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "Profile.csv",
            "First Name,Last Name,Headline,Summary\n"
            "Jane,Doe,Data Scientist,\"I ship ML models in Python and SQL.\"\n",
        )
        zf.writestr("Skills.csv", "Name\nPython\nMachine Learning\nSQL\nPandas\n")
    r = client.post(
        "/api/v1/analyze/upload",
        files={"file": ("export.zip", buf.getvalue(), "application/zip")},
    )
    assert r.status_code == 200
    assert r.json()["parsed"]["name"] == "Jane Doe"


def test_upload_rejects_garbage(client):
    r = client.post(
        "/api/v1/analyze/upload",
        files={"file": ("x.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 40, "image/png")},
    )
    assert r.status_code == 422


def test_career_and_assistant_endpoints(client):
    assert client.post("/api/v1/career/predict",
                       json={"profile_text": ARCHETYPES["average"]}).status_code == 200
    assert client.post("/api/v1/assistant/headline",
                       json={"headline": "Student", "skills": ["python"]}).status_code == 200
    assert client.post("/api/v1/assistant/about",
                       json={"skills": ["python"], "experience_years": 2}).status_code == 200
