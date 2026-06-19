import { useEffect, useState } from 'react'
import { scoreColor } from '../lib/format'

interface Props {
  value: number
  size?: number
  stroke?: number
  label?: string
}

/** Animated circular gauge that counts up to `value` (0–100). */
export default function ScoreGauge({ value, size = 150, stroke = 12, label }: Props) {
  const [display, setDisplay] = useState(0)
  const radius = (size - stroke) / 2
  const circ = 2 * Math.PI * radius
  const offset = circ - (display / 100) * circ
  const color = scoreColor(value)

  useEffect(() => {
    let raf = 0
    const start = performance.now()
    const tick = (now: number) => {
      const t = Math.min((now - start) / 1100, 1)
      const eased = 1 - Math.pow(1 - t, 3)
      setDisplay(Math.round(value * eased))
      if (t < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [value])

  return (
    <div className="relative grid place-items-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="rgba(148,163,184,0.15)" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circ}
          strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 0.2s linear', filter: `drop-shadow(0 0 6px ${color}66)` }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-4xl font-extrabold text-white tabular-nums">{display}</span>
        {label && <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400">{label}</span>}
      </div>
    </div>
  )
}
