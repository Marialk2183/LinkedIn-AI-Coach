import type { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Sparkles } from 'lucide-react'

function Navbar() {
  const { pathname } = useLocation()
  return (
    <header className="no-print sticky top-0 z-30 w-full">
      <div className="glass border-x-0 border-t-0">
        <nav className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
          <Link to="/" className="group flex items-center gap-2.5">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-brand-600 shadow-glow transition-transform group-hover:scale-105">
              <Sparkles className="h-5 w-5 text-white" />
            </span>
            <span className="text-base font-extrabold tracking-tight text-white sm:text-lg">
              LinkedIn <span className="gradient-text">AI Coach</span>
            </span>
          </Link>
          <div className="flex items-center gap-2">
            {pathname !== '/analyze' && (
              <Link to="/analyze" className="btn-ghost px-4 py-2 text-sm">
                Analyze
              </Link>
            )}
          </div>
        </nav>
      </div>
    </header>
  )
}

function Background() {
  return (
    <div aria-hidden className="no-print pointer-events-none fixed inset-0 z-0 overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-b from-ink-900 via-ink-950 to-ink-950" />
      <div className="absolute -left-32 -top-32 h-96 w-96 rounded-full bg-brand-600/25 blur-3xl animate-float" />
      <div className="absolute right-[-10%] top-24 h-[28rem] w-[28rem] rounded-full bg-indigo-600/20 blur-3xl animate-float [animation-delay:1.5s]" />
      <div className="absolute bottom-[-10%] left-1/3 h-96 w-96 rounded-full bg-sky-500/15 blur-3xl animate-float [animation-delay:3s]" />
    </div>
  )
}

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="relative flex min-h-screen flex-col overflow-x-hidden">
      <Background />
      <Navbar />
      <main className="relative z-10 flex-1">{children}</main>
      <footer className="relative z-10 border-t border-white/10">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-3 px-4 py-8 text-xs text-slate-500 sm:flex-row sm:px-6 lg:px-8">
          <span>LinkedIn AI Coach &copy; {new Date().getFullYear()}</span>
          <span>Not affiliated with LinkedIn. Manual text analysis only — no scraping.</span>
        </div>
      </footer>
    </div>
  )
}
