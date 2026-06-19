export type Tier = 'excellent' | 'good' | 'fair' | 'weak'

export function tier(score: number): Tier {
  if (score >= 80) return 'excellent'
  if (score >= 65) return 'good'
  if (score >= 50) return 'fair'
  return 'weak'
}

export function tierLabel(score: number): string {
  return { excellent: 'Excellent', good: 'Good', fair: 'Needs work', weak: 'Weak' }[tier(score)]
}

/** Hex color for a score, used by charts and gauges. */
export function scoreColor(score: number): string {
  return { excellent: '#34d399', good: '#60a5fa', fair: '#fbbf24', weak: '#fb7185' }[tier(score)]
}

export function tierChip(score: number): string {
  return {
    excellent: 'bg-emerald-500/15 text-emerald-300 ring-emerald-500/30',
    good: 'bg-brand-500/15 text-brand-300 ring-brand-500/30',
    fair: 'bg-amber-500/15 text-amber-300 ring-amber-500/30',
    weak: 'bg-rose-500/15 text-rose-300 ring-rose-500/30',
  }[tier(score)]
}

export function titleCase(s: string): string {
  return s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}
