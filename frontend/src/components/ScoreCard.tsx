import { useEffect, useState } from 'react'
import type { LucideIcon } from 'lucide-react'
import { scoreColor, tierChip, tierLabel } from '../lib/format'

interface Props {
  icon: LucideIcon
  title: string
  score: number
  hint?: string
  delay?: number
}

export default function ScoreCard({ icon: Icon, title, score, hint, delay = 0 }: Props) {
  const [width, setWidth] = useState(0)
  const color = scoreColor(score)

  useEffect(() => {
    const id = setTimeout(() => setWidth(score), 150 + delay)
    return () => clearTimeout(id)
  }, [score, delay])

  return (
    <div
      className="card group transition-all duration-300 hover:-translate-y-1 hover:border-white/20 hover:shadow-glow animate-fade-up"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-white/5 ring-1 ring-white/10">
            <Icon className="h-5 w-5" style={{ color }} />
          </span>
          <h3 className="text-sm font-semibold text-slate-200">{title}</h3>
        </div>
        <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ring-1 ${tierChip(score)}`}>
          {tierLabel(score)}
        </span>
      </div>

      <div className="mt-5">
        <span className="text-4xl font-extrabold tabular-nums" style={{ color }}>
          {score}
          <span className="ml-0.5 text-lg font-bold text-slate-500">/100</span>
        </span>
      </div>

      <div className="mt-4 h-2 w-full overflow-hidden rounded-full bg-white/10">
        <div
          className="h-full rounded-full transition-[width] duration-1000 ease-out"
          style={{ width: `${width}%`, background: `linear-gradient(90deg, ${color}99, ${color})`, boxShadow: `0 0 12px ${color}66` }}
        />
      </div>

      {hint && <p className="mt-4 text-sm leading-relaxed text-slate-400">{hint}</p>}
    </div>
  )
}
