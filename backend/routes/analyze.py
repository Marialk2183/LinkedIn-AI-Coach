"""/analyze, file upload, analysis history, and PDF report endpoints."""

import re

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import orm
from models.schemas import (
    AnalysisResponse,
    AnalyzeRequest,
    CareerMatchSchema,
    RecommendationSchema,
    ScoresSchema,
)
from routes.deps import get_analysis_service, get_artifact_store
from services.analysis_service import AnalysisService
from services.report_service import REPORT_VERSION, build_report_pdf
from services.storage import ArtifactStore
from utils.extract import extract_text

router = APIRouter(tags=["analysis"])


def _slug(name: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (name or "profile").lower()).strip("-") or "profile"


def _pdf_attachment(pdf: bytes, slug: str) -> Response:
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{slug}-report.pdf"'},
    )


def _pdf_response(result: AnalysisResponse) -> Response:
    """Render a report to PDF and return it as a downloadable attachment."""
    return _pdf_attachment(build_report_pdf(result), _slug(result.parsed.name))


@router.post("/analyze", response_model=AnalysisResponse)
def analyze(
    payload: AnalyzeRequest,
    db: Session = Depends(get_db),
    service: AnalysisService = Depends(get_analysis_service),
) -> AnalysisResponse:
    try:
        return service.analyze(
            db, source_type=payload.source_type, profile_text=payload.profile_text
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


@router.post("/analyze/upload", response_model=AnalysisResponse)
async def analyze_upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    service: AnalysisService = Depends(get_analysis_service),
) -> AnalysisResponse:
    """Analyze an uploaded file: a PDF resume, a .txt, or a LinkedIn data-export .zip."""
    data = await file.read()
    try:
        text = extract_text(file.filename or "", data)
        return service.analyze(db, source_type="export", profile_text=text)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


@router.post(
    "/report/pdf",
    responses={200: {"content": {"application/pdf": {}}}},
    response_class=Response,
)
def report_pdf(result: AnalysisResponse) -> Response:
    """Generate a recruiter-style PDF from an analysis result (full fidelity).

    The frontend posts the in-memory result it already has, so impact points and
    worked examples are preserved (they aren't all persisted on the row).
    """
    return _pdf_response(result)


@router.get(
    "/analyses/{analysis_id}/report.pdf",
    responses={200: {"content": {"application/pdf": {}}}},
    response_class=Response,
)
def report_pdf_by_id(
    analysis_id: int,
    db: Session = Depends(get_db),
    store: ArtifactStore = Depends(get_artifact_store),
) -> Response:
    """Generate (and cache) the PDF for a stored analysis (history view).

    Analyses are immutable, so the PDF is cached in the artifact store (local
    filesystem by default, Azure Blob when configured) and re-served from there.
    """
    row = db.get(orm.Analysis, analysis_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    # Version the key so a changed report template invalidates old cached PDFs.
    key = f"reports/v{REPORT_VERSION}/{analysis_id}.pdf"
    response = _row_to_response(row)
    pdf = None
    try:
        pdf = store.load(key)
    except Exception:  # noqa: BLE001 - a bad cache entry must not fail the request
        pdf = None
    if pdf is None:
        pdf = build_report_pdf(response)
        try:
            store.save(key, pdf, "application/pdf")
        except Exception:  # noqa: BLE001 - caching is best-effort, never fail the request
            pass
    return _pdf_attachment(pdf, _slug(response.parsed.name))


@router.get("/analyses/{analysis_id}", response_model=AnalysisResponse)
def get_analysis(analysis_id: int, db: Session = Depends(get_db)) -> AnalysisResponse:
    row = db.get(orm.Analysis, analysis_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return _row_to_response(row)


@router.get("/analyses")
def list_analyses(db: Session = Depends(get_db), limit: int = 20) -> list[dict]:
    rows = db.scalars(
        select(orm.Analysis).order_by(orm.Analysis.created_at.desc()).limit(limit)
    ).all()
    return [
        {
            "analysis_id": r.id,
            "name": r.profile.name,
            "headline": r.profile.headline,
            "overall": r.overall,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


def _row_to_response(row: orm.Analysis) -> AnalysisResponse:
    """Reconstruct a response from persisted rows (history view)."""
    from models.schemas import AIWritingSchema, ParsedSummary

    parsed = row.profile.parsed_json or {}
    strengths = [r.content for r in row.recommendations if r.category == "strength"]
    weaknesses = [r.content for r in row.recommendations if r.category == "weakness"]
    recs = [
        RecommendationSchema(category=r.category, content=r.content)
        for r in row.recommendations
        if r.category not in ("strength", "weakness")
    ]
    ai = {o.kind: o.content for o in row.ai_outputs}
    # ATS/Leadership aren't separate columns — read them from the persisted
    # breakdown (older rows simply default to 0).
    bd = row.breakdown_json or {}
    ats = int(bd.get("ats", {}).get("score", 0))
    leadership = int(bd.get("leadership", {}).get("score", 0))
    return AnalysisResponse(
        analysis_id=row.id,
        source_type=row.profile.source_type,  # type: ignore[arg-type]
        scores=ScoresSchema(
            overall=row.overall, completeness=row.completeness, technical=row.technical,
            recruiter=row.recruiter, networking=row.networking,
            career_readiness=row.career_readiness, ats=ats, leadership=leadership,
        ),
        breakdown={},
        ml_used=row.ml_used,
        parsed=ParsedSummary(**parsed) if parsed else ParsedSummary(),
        strengths=strengths,
        weaknesses=weaknesses,
        recommendations=recs,
        career_predictions=[
            CareerMatchSchema(role=c.role, match_pct=c.match_pct)
            for c in row.career_predictions
        ],
        ai_writing=AIWritingSchema(headline=ai.get("headline"), about=ai.get("about")),
    )
