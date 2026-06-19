import { CheckCircle2, AlertTriangle, Lightbulb } from 'lucide-react'
import type { RecommendationItem } from '../types/analysis'
import { titleCase } from '../lib/format'

interface Props {
  strengths: string[]
  weaknesses: string[]
  recommendations: RecommendationItem[]
}

export default function RecommendationsPanel({ strengths, weaknesses, recommendations }: Props) {
  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <div className="card">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="h-5 w-5 text-emerald-400" />
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300">Strengths</h3>
        </div>
        <ul className="mt-4 space-y-3">
          {strengths.map((s, i) => (
            <li key={i} className="flex items-start gap-3 rounded-xl bg-emerald-500/5 p-3 ring-1 ring-emerald-500/10">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
              <span className="text-sm text-slate-300">{s}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="card">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-amber-400" />
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300">Weaknesses</h3>
        </div>
        <ul className="mt-4 space-y-3">
          {weaknesses.map((w, i) => (
            <li key={i} className="flex items-start gap-3 rounded-xl bg-amber-500/5 p-3 ring-1 ring-amber-500/10">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
              <span className="text-sm text-slate-300">{w}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="card lg:col-span-2">
        <div className="flex items-center gap-2">
          <Lightbulb className="h-5 w-5 text-brand-300" />
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
            Actionable Recommendations
          </h3>
        </div>
        <ul className="mt-4 grid gap-3 sm:grid-cols-2">
          {recommendations.map((r, i) => (
            <li key={i} className="rounded-xl bg-white/5 p-3 ring-1 ring-white/5">
              <div className="flex items-start gap-3">
                <span className="mt-0.5 rounded-md bg-brand-500/15 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-brand-300">
                  {titleCase(r.category)}
                </span>
                <span className="text-sm leading-relaxed text-slate-300">
                  {r.content.replace(/\s*\(~\+\d+ pts\)\s*$/, '')}
                </span>
                {r.impact_points ? (
                  <span className="ml-auto mt-0.5 shrink-0 rounded-md bg-emerald-500/15 px-2 py-0.5 text-[10px] font-semibold text-emerald-300">
                    +{r.impact_points} pts
                  </span>
                ) : null}
              </div>
              {r.example ? (
                <p className="mt-2 border-l-2 border-brand-500/30 pl-3 text-xs italic leading-relaxed text-slate-400">
                  {r.example}
                </p>
              ) : null}
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
