"""Server-side, recruiter-style PDF report generation (ReportLab).

Turns an :class:`~models.schemas.AnalysisResponse` into a professional,
branded PDF a candidate can hand to a recruiter or keep as a record. Pure and
side-effect free: ``build_report_pdf`` takes the analysis and returns ``bytes``,
so it can be served from a route today and pushed to Azure Blob / generated in
an Azure Function later without changing this module.

Layout (recruiter-report convention):

    Branding header → Executive Summary → Overall Score → Score Breakdown
    (with the formula behind each dimension) → dimension bar chart →
    ATS Readiness → Strengths → Weaknesses → Skill-Gap Analysis →
    Career Recommendations → Career-Match chart → Learning Roadmap →
    Recruiter Feedback → AI Writing Suggestions → footer/disclaimer.

No FastAPI import here on purpose — this stays a plain service the API layer
calls, consistent with the project's inward dependency rule.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone

from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from models.schemas import AnalysisResponse

# Bump whenever the report layout/content changes so cached PDFs (keyed by this
# version in the artifact store) are regenerated rather than served stale.
REPORT_VERSION = 1

# --- brand palette ---------------------------------------------------------- #
BRAND = colors.HexColor("#4f46e5")       # indigo-600
BRAND_DARK = colors.HexColor("#3730a3")  # indigo-800
INK = colors.HexColor("#0f172a")         # slate-900
MUTED = colors.HexColor("#475569")       # slate-600
LINE = colors.HexColor("#e2e8f0")        # slate-200

# Dimension -> the formula it's computed from (kept in sync with
# services.scoring_service so the PDF can explain *why* a score is what it is).
DIMENSION_FORMULAS: dict[str, str] = {
    "Completeness": "0.22·About + 0.20·Experience + 0.15·Headline + "
    "0.12·Projects + 0.11·Certs + 0.10·Education + 0.10·Skills",
    "Technical Strength": "0.45·Technical-skills + 0.25·Projects + "
    "0.20·Experience + 0.10·Certifications",
    "Recruiter Appeal": "0.30·Headline-quality + 0.25·About-quality + "
    "0.25·Skill-relevance + 0.20·Experience-quality",
    "Networking": "0.45·Connections + 0.40·Activity + 0.15·Followers "
    "(activity-only is capped at 70%)",
    "Career Readiness": "0.35·Technical-depth + 0.25·Experience + "
    "0.20·Credentials + 0.20·Completeness",
    "ATS Score": "0.30·Section-structure + 0.25·Keyword-coverage + "
    "0.20·Technical-keywords + 0.15·Headline-role-keyword + 0.10·Quantified-impact",
    "Leadership": "0.35·Experience-seniority + 0.30·Leadership-language + "
    "0.20·Seniority-title + 0.15·Leadership-skills",
}


def _tier(score: int) -> tuple[str, colors.Color]:
    """Recruiter-facing band label + color for an overall/dimension score."""
    if score >= 85:
        return "All-Star", colors.HexColor("#16a34a")   # green-600
    if score >= 70:
        return "Strong", colors.HexColor("#65a30d")      # lime-600
    if score >= 55:
        return "Solid", colors.HexColor("#ca8a04")       # yellow-600
    if score >= 40:
        return "Developing", colors.HexColor("#ea580c")  # orange-600
    return "Needs Work", colors.HexColor("#dc2626")      # red-600


def _esc(value: str | None) -> str:
    """Escape user/profile text for ReportLab's mini-HTML paragraph parser."""
    s = value or ""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    body = base["BodyText"]
    body.fontName = "Helvetica"
    body.fontSize = 9.5
    body.leading = 14
    body.textColor = INK
    return {
        "title": ParagraphStyle(
            "title", parent=body, fontName="Helvetica-Bold", fontSize=22,
            leading=26, textColor=colors.white,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", parent=body, fontSize=10.5, leading=14,
            textColor=colors.HexColor("#c7d2fe"),
        ),
        "h2": ParagraphStyle(
            "h2", parent=body, fontName="Helvetica-Bold", fontSize=13,
            leading=16, textColor=BRAND_DARK, spaceBefore=14, spaceAfter=4,
        ),
        "body": body,
        "muted": ParagraphStyle("muted", parent=body, textColor=MUTED, fontSize=9),
        "lead": ParagraphStyle("lead", parent=body, fontSize=10.5, leading=15),
        "formula": ParagraphStyle(
            "formula", parent=body, fontName="Helvetica-Oblique", fontSize=7.5,
            leading=10, textColor=MUTED,
        ),
        "footer": ParagraphStyle(
            "footer", parent=body, fontSize=7.5, textColor=MUTED, alignment=TA_CENTER,
        ),
        "big": ParagraphStyle(
            "big", parent=body, fontName="Helvetica-Bold", fontSize=44,
            leading=46, textColor=BRAND, alignment=TA_CENTER,
        ),
    }


# --- derived narrative ------------------------------------------------------ #
def _executive_summary(result: AnalysisResponse) -> str:
    name = (result.parsed.name or "This candidate").strip()
    overall = result.scores.overall
    label, _ = _tier(overall)
    top = result.recommendations[0].content if result.recommendations else None
    strength = result.strengths[0] if result.strengths else None
    role = result.career_predictions[0].role if result.career_predictions else None

    parts = [
        f"{_esc(name)} scores <b>{overall}/100</b> overall, placing the profile in "
        f"the <b>{label}</b> band"
        + (" (ML-calibrated)." if result.ml_used else ".")
    ]
    if role:
        match = result.career_predictions[0].match_pct
        parts.append(
            f" The strongest career alignment is <b>{_esc(role)}</b> at "
            f"<b>{match:.0f}%</b> match."
        )
    if strength:
        parts.append(f" Key strength: {_esc(strength.rstrip('.'))}.")
    if top:
        clean = top.split(" (~+")[0]
        parts.append(f" Highest-impact next step: {_esc(clean.rstrip('.'))}.")
    return "".join(parts)


def _learning_roadmap(result: AnalysisResponse) -> list[str]:
    steps: list[str] = []
    top = result.career_predictions[0] if result.career_predictions else None
    if top and top.missing_skills:
        gap = ", ".join(s.title() for s in top.missing_skills[:3])
        steps.append(
            f"<b>0–30 days:</b> Close the top skill gap for {_esc(top.role)} — "
            f"start hands-on with {_esc(gap)} and ship one small project using it."
        )
    else:
        steps.append(
            "<b>0–30 days:</b> Pick one in-demand skill adjacent to your target "
            "role and build a small, public project demonstrating it."
        )
    steps.append(
        "<b>30–60 days:</b> Earn one recognized certification that validates your "
        "strongest skill, and rewrite your headline + About around it."
    )
    steps.append(
        "<b>60–90 days:</b> Quantify every experience bullet (%, $, time saved), "
        "publish your project write-up, and grow toward 500+ connections."
    )
    return steps


# --- charts ----------------------------------------------------------------- #
def _dimension_chart(result: AnalysisResponse) -> Drawing:
    s = result.scores
    rows = [
        ("Completeness", s.completeness),
        ("Technical", s.technical),
        ("Recruiter", s.recruiter),
        ("Networking", s.networking),
        ("Career Ready", s.career_readiness),
        ("ATS", s.ats),
        ("Leadership", s.leadership),
        ("Overall", s.overall),
    ]
    return _hbar(rows, title=None, bar_color=BRAND)


def _career_chart(result: AnalysisResponse) -> Drawing | None:
    if not result.career_predictions:
        return None
    rows = [(m.role, int(round(m.match_pct))) for m in result.career_predictions[:6]]
    return _hbar(rows, title=None, bar_color=BRAND_DARK)


def _hbar(rows: list[tuple[str, int]], *, title: str | None, bar_color: colors.Color) -> Drawing:
    height = 22 * len(rows) + 24
    d = Drawing(440, height)
    chart = HorizontalBarChart()
    chart.x = 110
    chart.y = 10
    chart.width = 280
    chart.height = height - 24
    chart.data = [[v for _, v in rows]]
    chart.bars[0].fillColor = bar_color
    chart.bars[0].strokeColor = None
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = 100
    chart.valueAxis.valueStep = 25
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.labels.fillColor = MUTED
    chart.categoryAxis.categoryNames = [name for name, _ in rows]
    chart.categoryAxis.labels.fontSize = 8
    chart.categoryAxis.labels.fillColor = INK
    chart.categoryAxis.labels.dx = -6
    chart.categoryAxis.labels.boxAnchor = "e"
    chart.barWidth = 11
    chart.groupSpacing = 6
    # Built-in value labels stay aligned with their bars (categories plot
    # bottom-up); drawing them by hand previously flipped the order.
    chart.barLabelFormat = "%d"
    chart.barLabels.fontSize = 7.5
    chart.barLabels.fillColor = MUTED
    chart.barLabels.boxAnchor = "w"
    chart.barLabels.dx = 5
    d.add(chart)
    return d


# --- flowable builders ------------------------------------------------------ #
def _bullet_list(items: list[str], st: dict[str, ParagraphStyle]) -> ListFlowable:
    return ListFlowable(
        [ListItem(Paragraph(_esc(i), st["body"]), leftIndent=10) for i in items],
        bulletType="bullet", bulletColor=BRAND, start="•", leftIndent=12,
    )


def _section(title: str, st: dict[str, ParagraphStyle]) -> list:
    return [
        Paragraph(title, st["h2"]),
        HRFlowable(width="100%", thickness=0.6, color=LINE, spaceAfter=6),
    ]


def _breakdown_table(result: AnalysisResponse, st: dict[str, ParagraphStyle]) -> Table:
    s = result.scores
    dims = [
        ("Completeness", s.completeness),
        ("Technical Strength", s.technical),
        ("Recruiter Appeal", s.recruiter),
        ("Networking", s.networking),
        ("Career Readiness", s.career_readiness),
        ("ATS Score", s.ats),
        ("Leadership", s.leadership),
    ]
    data = [["Dimension", "Score", "Formula"]]
    for name, val in dims:
        label, _ = _tier(val)
        data.append([
            Paragraph(f"<b>{name}</b><br/><font size=7 color='#475569'>{label}</font>", st["body"]),
            Paragraph(f"<b>{val}</b>", st["body"]),
            Paragraph(DIMENSION_FORMULAS.get(name, ""), st["formula"]),
        ])
    table = Table(data, colWidths=[42 * mm, 16 * mm, 102 * mm], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
    ]))
    return table


def _footer(canvas, doc) -> None:
    """Brand + page number along the bottom of every page."""
    canvas.saveState()
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawRightString(A4[0] - 18 * mm, 12 * mm, f"Page {doc.page}")
    canvas.drawString(18 * mm, 12 * mm, "LinkedIn AI Coach")
    canvas.restoreState()


def _make_first_page(name: str, headline: str, date: str):
    """Build the page-1 painter: the indigo brand band with title text on it.

    Drawn on the canvas (not as flowables) so the white title sits *inside* the
    band instead of below it on white."""

    def draw(canvas, doc) -> None:
        top = A4[1]
        canvas.saveState()
        canvas.setFillColor(BRAND_DARK)
        canvas.rect(0, top - 34 * mm, A4[0], 34 * mm, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 20)
        canvas.drawString(18 * mm, top - 15 * mm, f"{name} — Profile Report")
        canvas.setFillColor(colors.HexColor("#c7d2fe"))
        canvas.setFont("Helvetica", 10)
        y = top - 22 * mm
        if headline:
            canvas.drawString(18 * mm, y, headline[:110])
            y -= 5 * mm
        canvas.drawString(18 * mm, y, f"Generated {date}")
        canvas.restoreState()
        _footer(canvas, doc)

    return draw


# --- entry point ------------------------------------------------------------ #
def build_report_pdf(result: AnalysisResponse) -> bytes:
    """Render the analysis into a recruiter-style PDF and return its bytes."""
    st = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=40 * mm, bottomMargin=18 * mm,
        title="LinkedIn AI Coach — Profile Report",
        author="LinkedIn AI Coach",
    )

    name = result.parsed.name or "Your Profile"
    headline = result.parsed.headline or ""
    date = datetime.now(timezone.utc).strftime("%B %d, %Y")
    overall = result.scores.overall
    o_label, o_color = _tier(overall)

    story: list = []

    # Title/subtitle/date are painted onto the brand band by the page-1 callback
    # (see _make_first_page); the flowable story starts at the first section.
    story += _section("Executive Summary", st)
    story.append(Paragraph(_executive_summary(result), st["lead"]))

    # Overall score block: big number + tier + ATS score, side by side.
    ats = result.scores.ats
    overall_cell = [
        Paragraph(str(overall), st["big"]),
        Paragraph(
            f"<font color='#{o_color.hexval()[2:]}'><b>{o_label}</b></font> · of 100"
            + ("<br/>ML-calibrated" if result.ml_used else ""),
            ParagraphStyle("oc", parent=st["muted"], alignment=TA_CENTER),
        ),
    ]
    ats_cell = [
        Paragraph(str(ats), ParagraphStyle("atsbig", parent=st["big"], textColor=BRAND_DARK)),
        Paragraph("ATS Score · of 100", ParagraphStyle("ac", parent=st["muted"], alignment=TA_CENTER)),
    ]
    score_table = Table([[overall_cell, ats_cell]], colWidths=[80 * mm, 80 * mm])
    score_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.6, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(Spacer(1, 4))
    story.append(score_table)

    # Score breakdown (with formulas) + chart
    story += _section("Score Breakdown", st)
    story.append(_breakdown_table(result, st))
    story.append(Spacer(1, 6))
    story.append(_dimension_chart(result))

    # ATS analysis
    story += _section("ATS Analysis", st)
    story.append(Paragraph(
        f"ATS score is <b>{ats}/100</b> — a deterministic blend of parseable section "
        f"structure ({result.scores.completeness}), searchable skill keywords "
        f"({result.parsed.skills_count} listed), a role-keyworded headline, and "
        "quantified, machine-readable impact. Applicant-tracking systems rank on "
        "exactly these signals, so the fixes below also lift this score.", st["body"]))

    # Strengths / Weaknesses
    if result.strengths:
        story += _section("Strengths", st)
        story.append(_bullet_list(result.strengths, st))
    if result.weaknesses:
        story += _section("Weaknesses", st)
        story.append(_bullet_list(result.weaknesses, st))

    # Skill-gap analysis (from top career match)
    if result.career_predictions:
        top = result.career_predictions[0]
        story += _section("Skill-Gap Analysis", st)
        story.append(Paragraph(
            f"Against your strongest match, <b>{_esc(top.role)}</b> "
            f"({top.match_pct:.0f}%):", st["body"]))
        if top.matched_skills:
            story.append(Paragraph(
                "<b>Matched:</b> " + _esc(", ".join(s.title() for s in top.matched_skills)),
                st["muted"]))
        if top.missing_skills:
            story.append(Paragraph(
                "<b>Missing:</b> " + _esc(", ".join(s.title() for s in top.missing_skills)),
                st["muted"]))

    # Career recommendations (impact-ranked, with worked examples)
    if result.recommendations:
        story += _section("Career Recommendations (highest impact first)", st)
        items = []
        for r in result.recommendations:
            content = _esc(r.content.split(" (~+")[0])
            pts = f" <font color='#16a34a'><b>(~+{r.impact_points} pts)</b></font>" if r.impact_points else ""
            block = f"{content}{pts}"
            if r.example:
                block += f"<br/><font size=8 color='#475569'>e.g. {_esc(r.example)}</font>"
            items.append(Paragraph(block, st["body"]))
        story.append(ListFlowable(
            [ListItem(i, leftIndent=10) for i in items],
            bulletType="1", bulletColor=BRAND, leftIndent=14,
        ))

    # Career match chart
    chart = _career_chart(result)
    if chart is not None:
        story += _section("Career Match", st)
        story.append(chart)

    # Learning roadmap
    story += _section("Learning Roadmap", st)
    story.append(ListFlowable(
        [ListItem(Paragraph(step, st["body"]), leftIndent=10) for step in _learning_roadmap(result)],
        bulletType="bullet", bulletColor=BRAND, start="•", leftIndent=12,
    ))

    # Recruiter feedback
    story += _section("Recruiter Feedback", st)
    story.append(Paragraph(
        f"A recruiter skimming this profile sees a <b>{o_label.lower()}</b> candidate. "
        + ("Lead with a keyword-rich headline and a quantified About section to win the "
           "6-second scan; "
           if result.scores.recruiter < 75 else
           "The headline and summary read well; ")
        + "the strengths above are your hook — make them the first thing visible, and "
        "address the weaknesses to remove easy reasons to pass.", st["body"]))

    # AI writing suggestions
    aw = result.ai_writing
    if aw.headline or aw.about:
        story += _section("AI Writing Suggestions", st)
        if aw.headline:
            story.append(Paragraph("<b>Suggested headline</b>", st["body"]))
            story.append(Paragraph(_esc(aw.headline), st["muted"]))
            story.append(Spacer(1, 4))
        if aw.about:
            story.append(Paragraph("<b>Suggested About</b>", st["body"]))
            for para in (aw.about or "").split("\n"):
                if para.strip():
                    story.append(Paragraph(_esc(para.strip()), st["muted"]))

    # Footer / disclaimer
    story.append(Spacer(1, 8 * mm))
    story.append(HRFlowable(width="100%", thickness=0.6, color=LINE, spaceAfter=4))
    story.append(Paragraph(
        "Generated by LinkedIn AI Coach · Not affiliated with LinkedIn. Scores are "
        "computed from the text you provided using transparent rule-based formulas "
        "blended with an ML model; see the score breakdown for the factors behind each.",
        st["footer"]))

    doc.build(
        story,
        onFirstPage=_make_first_page(name, headline, date),
        onLaterPages=_footer,
    )
    return buf.getvalue()
