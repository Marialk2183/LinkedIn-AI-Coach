"""SQLAlchemy ORM models. JSON columns are portable across SQLite/Postgres."""

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_type: Mapped[str] = mapped_column(String(20), default="text")
    raw_text: Mapped[str] = mapped_column(Text, default="")
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    headline: Mapped[str | None] = mapped_column(String(400), nullable=True)
    parsed_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    analyses: Mapped[list["Analysis"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), index=True)

    overall: Mapped[int] = mapped_column(Integer)
    completeness: Mapped[int] = mapped_column(Integer)
    technical: Mapped[int] = mapped_column(Integer)
    recruiter: Mapped[int] = mapped_column(Integer)
    networking: Mapped[int] = mapped_column(Integer)
    career_readiness: Mapped[int] = mapped_column(Integer)

    breakdown_json: Mapped[dict] = mapped_column(JSON, default=dict)
    ml_used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    profile: Mapped["Profile"] = relationship(back_populates="analyses")
    recommendations: Mapped[list["Recommendation"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )
    career_predictions: Mapped[list["CareerPrediction"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )
    ai_outputs: Mapped[list["AiOutput"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("analyses.id"), index=True)
    category: Mapped[str] = mapped_column(String(40))  # strength|weakness|missing_*|action
    content: Mapped[str] = mapped_column(Text)

    analysis: Mapped["Analysis"] = relationship(back_populates="recommendations")


class CareerPrediction(Base):
    __tablename__ = "career_predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("analyses.id"), index=True)
    role: Mapped[str] = mapped_column(String(80))
    match_pct: Mapped[float] = mapped_column(Float)

    analysis: Mapped["Analysis"] = relationship(back_populates="career_predictions")


class AiOutput(Base):
    __tablename__ = "ai_outputs"

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("analyses.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40))  # headline|about|advice
    content: Mapped[str] = mapped_column(Text)

    analysis: Mapped["Analysis"] = relationship(back_populates="ai_outputs")
