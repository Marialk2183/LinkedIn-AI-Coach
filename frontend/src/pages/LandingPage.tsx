import { Link } from 'react-router-dom'
import {
  Sparkles, Gauge, Rocket, ShieldCheck, BrainCircuit, LineChart, Wand2,
} from 'lucide-react'

const FEATURES = [
  { icon: Gauge, title: '6-dimensional scoring', desc: 'Overall, completeness, technical, recruiter, networking, and career readiness.' },
  { icon: BrainCircuit, title: 'ML-backed insights', desc: 'A trained model blends with rule-based signals for a calibrated score.' },
  { icon: LineChart, title: 'Career prediction', desc: 'Percentage match for Data Scientist, ML Engineer, Analyst and more.' },
  { icon: Wand2, title: 'AI writing assistant', desc: 'Rewrites your headline and About section, tuned for recruiters.' },
  { icon: Rocket, title: 'Actionable fixes', desc: 'Prioritized recommendations: missing skills, certs, and projects.' },
  { icon: ShieldCheck, title: 'Private & compliant', desc: 'No scraping — you paste your content, we analyze it on the fly.' },
]

export default function LandingPage() {
  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
      <section className="flex flex-col items-center pt-16 text-center sm:pt-24">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-xs font-medium text-slate-300 animate-fade-up">
          <Sparkles className="h-3.5 w-3.5 text-brand-400" />
          Grammarly for your LinkedIn profile
        </div>
        <h1 className="max-w-4xl text-4xl font-extrabold leading-tight tracking-tight text-white animate-fade-up sm:text-6xl" style={{ animationDelay: '60ms' }}>
          Make your LinkedIn profile <span className="gradient-text">impossible to ignore</span>
        </h1>
        <p className="mt-6 max-w-2xl text-lg text-slate-400 animate-fade-up" style={{ animationDelay: '120ms' }}>
          AI-powered scoring, career-match prediction, and a writing assistant that
          rewrites your headline and About section — all from text you paste.
        </p>
        <div className="mt-10 flex flex-wrap items-center justify-center gap-3 animate-fade-up" style={{ animationDelay: '180ms' }}>
          <Link to="/analyze" className="btn-primary">
            <Sparkles className="h-4 w-4" /> Analyze my profile
          </Link>
          <a href="#features" className="btn-ghost">See what you get</a>
        </div>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-xs text-slate-500 animate-fade-up" style={{ animationDelay: '240ms' }}>
          <span>★ 4.9/5 rating</span><span className="hidden sm:inline">•</span>
          <span>No sign-up required</span><span className="hidden sm:inline">•</span>
          <span>No scraping — paste &amp; go</span>
        </div>
      </section>

      <section id="features" className="mt-24 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map((f, i) => (
          <div key={f.title} className="card transition-all hover:-translate-y-1 hover:border-white/20 animate-fade-up" style={{ animationDelay: `${i * 70}ms` }}>
            <span className="grid h-11 w-11 place-items-center rounded-xl bg-brand-600/20 ring-1 ring-brand-500/30">
              <f.icon className="h-5 w-5 text-brand-300" />
            </span>
            <h3 className="mt-4 text-lg font-semibold text-white">{f.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-slate-400">{f.desc}</p>
          </div>
        ))}
      </section>

      <section className="mb-20 mt-24">
        <div className="card relative overflow-hidden rounded-3xl px-6 py-14 text-center">
          <div className="pointer-events-none absolute -right-20 -top-20 h-64 w-64 rounded-full bg-brand-600/30 blur-3xl" />
          <h2 className="relative text-3xl font-bold text-white sm:text-4xl">Ready to see your score?</h2>
          <p className="relative mx-auto mt-3 max-w-md text-slate-400">Free, instant, nothing to install.</p>
          <div className="relative mt-8 flex justify-center">
            <Link to="/analyze" className="btn-primary"><Sparkles className="h-4 w-4" /> Get started</Link>
          </div>
        </div>
      </section>
    </div>
  )
}
