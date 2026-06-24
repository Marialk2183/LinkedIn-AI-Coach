import { useState } from 'react'
import { useLocation, useNavigate, Link } from 'react-router-dom'
import {
  ArrowLeft, ClipboardCheck, Cpu, UserSearch, Users, Briefcase, BadgeCheck,
  Download, FileJson, Printer, FileText, Loader2, ScanSearch, Crown,
} from 'lucide-react'
import type { AnalysisResponse } from '../types/analysis'
import { apiErrorMessage } from '../api/client'
import ScoreGauge from '../components/ScoreGauge'
import ScoreCard from '../components/ScoreCard'
import ScoreRadar from '../components/ScoreRadar'
import CareerChart from '../components/CareerChart'
import RecommendationsPanel from '../components/RecommendationsPanel'
import AIWritingCard from '../components/AIWritingCard'
import { tierChip, tierLabel } from '../lib/format'
import { exportJson, exportMarkdown, exportPdf, printReport } from '../lib/report'

export default function DashboardPage() {
  const navigate = useNavigate()
  const { state } = useLocation() as { state: { result?: AnalysisResponse } | null }
  const result = state?.result
  const [pdfLoading, setPdfLoading] = useState(false)
  const [pdfError, setPdfError] = useState<string | null>(null)

  async function handlePdf() {
    if (!result) return
    setPdfError(null)
    setPdfLoading(true)
    try {
      await exportPdf(result)
    } catch (err) {
      setPdfError(apiErrorMessage(err))
    } finally {
      setPdfLoading(false)
    }
  }

  if (!result) {
    return (
      <div className="mx-auto flex max-w-md flex-col items-center px-4 py-32 text-center">
        <h1 className="text-2xl font-bold text-white">No analysis yet</h1>
        <p className="mt-3 text-slate-400">Analyze a profile to see your dashboard.</p>
        <Link to="/analyze" className="btn-primary mt-8"><ArrowLeft className="h-4 w-4" /> Analyze a profile</Link>
      </div>
    )
  }

  const { scores, parsed, career_predictions, ai_writing } = result
  const cards = [
    { icon: ClipboardCheck, title: 'Profile Completeness', score: scores.completeness },
    { icon: Cpu, title: 'Technical Strength', score: scores.technical },
    { icon: UserSearch, title: 'Recruiter Appeal', score: scores.recruiter },
    { icon: ScanSearch, title: 'ATS Score', score: scores.ats },
    { icon: Crown, title: 'Leadership', score: scores.leadership },
    { icon: Users, title: 'Networking', score: scores.networking },
    { icon: Briefcase, title: 'Career Readiness', score: scores.career_readiness },
  ]

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <button onClick={() => navigate('/analyze')} className="mb-3 inline-flex items-center gap-1.5 text-sm text-slate-400 hover:text-white">
            <ArrowLeft className="h-4 w-4" /> Analyze another
          </button>
          <h1 className="text-3xl font-extrabold text-white sm:text-4xl">
            {parsed.name ? `${parsed.name}'s` : 'Your'} <span className="gradient-text">Profile Report</span>
          </h1>
          {parsed.headline && <p className="mt-1 text-slate-400">{parsed.headline}</p>}
        </div>
        <div className="flex flex-col items-start gap-3 sm:items-end">
          {result.ml_used && (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-white/5 px-3 py-1.5 text-xs text-slate-300 ring-1 ring-white/10">
              <BadgeCheck className="h-3.5 w-3.5 text-brand-300" /> ML-calibrated score
            </span>
          )}
          <div className="no-print flex flex-wrap items-center gap-2">
            <button
              onClick={handlePdf}
              disabled={pdfLoading}
              className="inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-brand-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {pdfLoading ? (
                <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Generating…</>
              ) : (
                <><FileText className="h-3.5 w-3.5" /> Download PDF</>
              )}
            </button>
            <button
              onClick={() => exportMarkdown(result)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-white/10"
            >
              <Download className="h-3.5 w-3.5" /> Markdown
            </button>
            <button
              onClick={() => exportJson(result)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-white/10"
            >
              <FileJson className="h-3.5 w-3.5" /> JSON
            </button>
            <button
              onClick={printReport}
              className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-white/10"
            >
              <Printer className="h-3.5 w-3.5" /> Print / PDF
            </button>
          </div>
          {pdfError && <p className="no-print text-xs text-rose-400">{pdfError}</p>}
        </div>
      </div>

      {/* Overall + radar */}
      <section className="mt-8 grid gap-5 lg:grid-cols-3">
        <div className="card flex items-center gap-6 lg:col-span-1">
          <ScoreGauge value={scores.overall} label="of 100" />
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">Overall Score</h2>
            <span className={`mt-2 inline-flex rounded-full px-3 py-1 text-xs font-semibold ring-1 ${tierChip(scores.overall)}`}>
              {tierLabel(scores.overall)}
            </span>
            <dl className="mt-4 space-y-1 text-sm text-slate-400">
              <div className="flex justify-between gap-6"><dt>Skills</dt><dd className="text-slate-200">{parsed.skills_count}</dd></div>
              <div className="flex justify-between gap-6"><dt>Projects</dt><dd className="text-slate-200">{parsed.projects_count}</dd></div>
              <div className="flex justify-between gap-6"><dt>Certifications</dt><dd className="text-slate-200">{parsed.certifications_count}</dd></div>
              <div className="flex justify-between gap-6"><dt>Experience</dt><dd className="text-slate-200">{parsed.experience_years} yrs</dd></div>
              {parsed.connections != null && (
                <div className="flex justify-between gap-6"><dt>Connections</dt><dd className="text-slate-200">{parsed.connections}</dd></div>
              )}
            </dl>
          </div>
        </div>
        <div className="lg:col-span-2">
          <ScoreRadar scores={scores} />
        </div>
      </section>

      {/* Metric cards */}
      <section className="mt-6 grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {cards.map((c, i) => (
          <ScoreCard key={c.title} icon={c.icon} title={c.title} score={c.score} delay={i * 80} />
        ))}
      </section>

      {/* Career + AI writing */}
      <section className="mt-6 grid gap-5 lg:grid-cols-2">
        <CareerChart matches={career_predictions} />
        <AIWritingCard writing={ai_writing} />
      </section>

      {/* Recommendations */}
      <section className="mt-6">
        <RecommendationsPanel
          strengths={result.strengths}
          weaknesses={result.weaknesses}
          recommendations={result.recommendations}
        />
      </section>
    </div>
  )
}
