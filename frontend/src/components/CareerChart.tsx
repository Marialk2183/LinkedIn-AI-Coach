import {
  Bar,
  BarChart,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { CareerMatch } from '../types/analysis'
import { scoreColor } from '../lib/format'

export default function CareerChart({ matches }: { matches: CareerMatch[] }) {
  const data = matches.map((m) => ({ role: m.role, pct: m.match_pct }))

  return (
    <div className="card">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
        Career Match Prediction
      </h3>
      <p className="mt-1 text-xs text-slate-500">
        Estimated fit for common industry roles, based on your skills + experience.
      </p>
      <div className="mt-4" style={{ height: data.length * 48 + 20 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            layout="vertical"
            margin={{ left: 10, right: 48, top: 4, bottom: 4 }}
          >
            <XAxis type="number" domain={[0, 100]} hide />
            <YAxis
              type="category"
              dataKey="role"
              width={130}
              tick={{ fill: '#cbd5e1', fontSize: 12 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              cursor={{ fill: 'rgba(255,255,255,0.04)' }}
              contentStyle={{
                background: '#0f172a',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: 12,
                color: '#e2e8f0',
              }}
              formatter={(v: number) => [`${v}%`, 'Match']}
            />
            <Bar dataKey="pct" radius={[6, 6, 6, 6]} barSize={20} isAnimationActive>
              {data.map((d, i) => (
                <Cell key={i} fill={scoreColor(d.pct)} />
              ))}
              <LabelList
                dataKey="pct"
                position="right"
                formatter={(v: number) => `${v}%`}
                fill="#e2e8f0"
                fontSize={12}
                fontWeight={700}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
