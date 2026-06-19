import {
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from 'recharts'
import type { Scores } from '../types/analysis'

export default function ScoreRadar({ scores }: { scores: Scores }) {
  const data = [
    { metric: 'Completeness', value: scores.completeness },
    { metric: 'Technical', value: scores.technical },
    { metric: 'Recruiter', value: scores.recruiter },
    { metric: 'Networking', value: scores.networking },
    { metric: 'Readiness', value: scores.career_readiness },
  ]

  return (
    <div className="card h-full">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
        Score Profile
      </h3>
      <div className="mt-2 h-72">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={data} outerRadius="72%">
            <PolarGrid stroke="rgba(148,163,184,0.2)" />
            <PolarAngleAxis
              dataKey="metric"
              tick={{ fill: '#94a3b8', fontSize: 12 }}
            />
            <Radar
              dataKey="value"
              stroke="#60a5fa"
              fill="#3b82f6"
              fillOpacity={0.45}
              isAnimationActive
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
