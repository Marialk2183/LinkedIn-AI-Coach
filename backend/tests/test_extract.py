"""Upload extraction: plain text, LinkedIn data-export .zip, and error paths."""

import io
import zipfile

import pytest

from utils.extract import UnsupportedUpload, extract_text


def _zip(files: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def test_plain_text_passthrough():
    raw = "Jane Doe\nData Scientist\nAbout\nI build ML models in Python.\n" * 2
    out = extract_text("profile.txt", raw.encode())
    assert "Data Scientist" in out
    assert "Python" in out


def test_linkedin_zip_rebuilds_sections():
    files = {
        "Profile.csv": (
            "First Name,Last Name,Headline,Summary\n"
            "Jane,Doe,Aspiring Data Scientist,"
            "\"I love turning data into decisions and shipping ML models.\"\n"
        ),
        "Positions.csv": (
            "Company Name,Title,Description,Started On,Finished On\n"
            "Acme,Data Science Intern,Built churn models in Python,Jan 2023,Dec 2023\n"
        ),
        "Skills.csv": "Name\nPython\nMachine Learning\nSQL\nPandas\n",
        "Certifications.csv": "Name,Authority\nGoogle Data Analytics,Google\n",
        "Projects.csv": "Title,Description\nChurn Predictor,Predicts churn with scikit-learn\n",
        "Education.csv": "School Name,Degree Name\nXYZ University,MCA\n",
        "Connections.csv": "First Name,Last Name\n" + "A,B\n" * 300,
    }
    out = extract_text("Basic_LinkedInDataExport.zip", _zip(files))
    assert "Jane Doe" in out
    assert "Aspiring Data Scientist" in out
    assert "About" in out and "Skills" in out and "Experience" in out
    assert "Python" in out
    assert "300 connections" in out


def test_empty_file_rejected():
    with pytest.raises(UnsupportedUpload):
        extract_text("x.txt", b"")


def test_unsupported_type_rejected():
    with pytest.raises(UnsupportedUpload):
        extract_text("image.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)


def test_zip_without_known_csvs_rejected():
    with pytest.raises(UnsupportedUpload):
        extract_text("random.zip", _zip({"notes.txt": "nothing useful here at all"}))
