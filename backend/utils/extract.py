"""Turn an uploaded file into plain profile text the parser understands.

Supports three things a user can realistically have without scraping:

* **PDF** — LinkedIn's own "Save to PDF" / a resume export.
* **Plain text** — `.txt` / `.md` they pasted into a file.
* **LinkedIn Data Export `.zip`** — the official archive LinkedIn emails you
  (Settings → Data privacy → Get a copy of your data). We read the known CSVs
  and rebuild them into sectioned text with the same headers the parser splits
  on (see ``utils.constants.SECTION_ALIASES``), so the rest of the pipeline is
  unchanged — a zip becomes text and flows through `parse_profile` like a paste.

Never raises on malformed input beyond a clear ``ValueError`` the route turns
into a 422; partial/odd archives degrade to whatever could be read.
"""

from __future__ import annotations

import csv
import io
import zipfile

# Generous ceiling — real exports/resumes are well under this.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


class UnsupportedUpload(ValueError):
    """Raised for an unreadable or unsupported upload."""


def extract_text(filename: str, data: bytes) -> str:
    """Dispatch on extension and return normalized profile text.

    Raises ``UnsupportedUpload`` if the file is empty, too large, of an
    unsupported type, or yields no readable text.
    """
    if not data:
        raise UnsupportedUpload("The uploaded file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        mb = MAX_UPLOAD_BYTES // (1024 * 1024)
        raise UnsupportedUpload(f"File is too large (max {mb} MB).")

    name = (filename or "").lower().strip()

    if name.endswith(".pdf"):
        text = _from_pdf(data)
    elif name.endswith(".zip"):
        text = _from_linkedin_zip(data)
    elif name.endswith((".txt", ".md", ".csv")) or _looks_like_text(data):
        text = _decode(data)
    else:
        raise UnsupportedUpload(
            "Unsupported file type. Upload a PDF, a .txt, or your LinkedIn "
            "data-export .zip."
        )

    text = text.strip()
    if len(text) < 20:
        raise UnsupportedUpload(
            "Couldn't read enough text from that file. If it's a scanned/image "
            "PDF, paste the text instead."
        )
    return text


# ----------------------------------------------------------------------------- #
def _decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore")


def _looks_like_text(data: bytes) -> bool:
    """Heuristic: a sample decodes cleanly and is mostly printable."""
    sample = data[:1024]
    try:
        sample.decode("utf-8")
    except UnicodeDecodeError:
        return False
    printable = sum(c >= 9 for c in sample)
    return printable / max(1, len(sample)) > 0.9


def _from_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependency declared in requirements
        raise UnsupportedUpload("PDF support is not installed on the server.") from exc
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [(page.extract_text() or "") for page in reader.pages]
    except Exception as exc:  # noqa: BLE001
        raise UnsupportedUpload("Couldn't read that PDF — it may be corrupted.") from exc
    return "\n".join(pages)


# --- LinkedIn data-export (.zip) -------------------------------------------- #
def _from_linkedin_zip(data: bytes) -> str:
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise UnsupportedUpload("That .zip couldn't be opened.") from exc

    # Map basename (lowercased) -> archive path, so nested folders still match.
    members = {name.rsplit("/", 1)[-1].lower(): name for name in zf.namelist()}

    def rows(basename: str) -> list[dict[str, str]]:
        path = members.get(basename.lower())
        if not path:
            return []
        try:
            raw = _decode(zf.read(path))
        except Exception:  # noqa: BLE001
            return []
        # LinkedIn sometimes prefixes a "Notes:" preamble before the CSV header.
        lines = raw.splitlines()
        for i, line in enumerate(lines):
            if "," in line:
                raw = "\n".join(lines[i:])
                break
        return [
            {(k or "").strip(): (v or "").strip() for k, v in row.items()}
            for row in csv.DictReader(io.StringIO(raw))
        ]

    parts: list[str] = []

    # Identity + headline + about, from Profile.csv.
    profile = rows("Profile.csv")
    if profile:
        p = profile[0]
        name = " ".join(x for x in [p.get("First Name"), p.get("Last Name")] if x)
        if name:
            parts.append(name)
        if p.get("Headline"):
            parts.append(p["Headline"])
        summary = p.get("Summary") or p.get("About")
        if summary:
            parts.append(f"About\n{summary}")

    # Experience, from Positions.csv.
    positions = rows("Positions.csv")
    if positions:
        block = ["Experience"]
        for pos in positions:
            title = pos.get("Title", "")
            company = pos.get("Company Name", "")
            start = pos.get("Started On", "")
            end = pos.get("Finished On", "") or "Present"
            header = " at ".join(x for x in [title, company] if x)
            dates = f" ({start} - {end})" if start else ""
            block.append(f"- {header}{dates}".rstrip())
            if pos.get("Description"):
                block.append(pos["Description"])
        parts.append("\n".join(block))

    # Education.
    education = rows("Education.csv")
    if education:
        block = ["Education"]
        for ed in education:
            degree = ed.get("Degree Name", "")
            school = ed.get("School Name", "")
            block.append(f"- {', '.join(x for x in [degree, school] if x)}".rstrip())
        parts.append("\n".join(block))

    # Skills (Skills.csv has a single "Name" column).
    skills = [r.get("Name", "") for r in rows("Skills.csv") if r.get("Name")]
    if skills:
        parts.append("Skills\n" + ", ".join(skills))

    # Certifications.
    certs = [r.get("Name", "") for r in rows("Certifications.csv") if r.get("Name")]
    if certs:
        parts.append("Certifications\n" + "\n".join(f"- {c}" for c in certs))

    # Projects.
    projects = rows("Projects.csv")
    if projects:
        block = ["Projects"]
        for pr in projects:
            title = pr.get("Title", "")
            if title:
                block.append(f"- {title}")
            if pr.get("Description"):
                block.append(pr["Description"])
        parts.append("\n".join(block))

    # Connections count = data rows in Connections.csv.
    connections = rows("Connections.csv")
    if connections:
        parts.append(f"{len(connections)} connections")

    if not parts:
        raise UnsupportedUpload(
            "No recognizable LinkedIn data found in that .zip. Make sure it's the "
            "archive from Settings → Get a copy of your data."
        )
    return "\n\n".join(parts)
