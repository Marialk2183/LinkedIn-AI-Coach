"""/analyze, file upload, and analysis history endpoints."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
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
from routes.deps import get_analysis_service
from services.analysis_service import AnalysisService
from utils.extract import extract_text

router = APIRouter(tags=["analysis"])


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
    return AnalysisResponse(
        analysis_id=row.id,
        source_type=row.profile.source_type,  # type: ignore[arg-type]
        scores=ScoresSchema(
            overall=row.overall, completeness=row.completeness, technical=row.technical,
            recruiter=row.recruiter, networking=row.networking,
            career_readiness=row.career_readiness,
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
