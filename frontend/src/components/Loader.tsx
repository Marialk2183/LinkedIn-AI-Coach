import { useEffect, useState } from 'react'
import { Sparkles } from 'lucide-react'

const STEPS = [
  'Parsing your profile…',
  'Scoring completeness & technical strength…',
  'Assessing recruiter appeal…',
  'Predicting career matches…',
  'Generating recommendations…',
]

export default function Loader() {
  const [step, setStep] = useState(0)
  useEffect(() => {
    const id = setInterval(() => setStep((s) => (s + 1) % STEPS.length), 800)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="flex flex-col items-center justify-center px-4 py-24 text-center">
      <div className="relative grid h-40 w-40 place-items-center">
        <span className="absolute inset-0 animate-ping rounded-full bg-brand-500/20" />
        <span className="absolute inset-0 animate-spin rounded-full border-2 border-transparent border-t-brand-400 border-r-brand-500 [animation-duration:1.1s]" />
        <span className="grid h-16 w-16 place-items-center rounded-2xl bg-brand-600 shadow-glow">
          <Sparkles className="h-8 w-8 animate-pulse text-white" />
        </span>
      </div>
      <h2 className="mt-10 text-2xl font-bold text-white">Analyzing your profile</h2>
      <div className="mt-3 h-6 overflow-hidden">
        <p key={step} className="animate-fade-up text-slate-400" aria-live="polite">
          {STEPS[step]}
        </p>
      </div>
      <div className="relative mt-8 h-1.5 w-64 overflow-hidden rounded-full bg-white/10">
        <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-brand-400 to-transparent" />
      </div>
    </div>
  )
}
