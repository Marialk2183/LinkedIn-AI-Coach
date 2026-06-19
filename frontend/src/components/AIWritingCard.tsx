import { useState } from 'react'
import { Wand2, Copy, Check } from 'lucide-react'
import type { AIWriting } from '../types/analysis'

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(text)
        setCopied(true)
        setTimeout(() => setCopied(false), 1500)
      }}
      className="btn-ghost px-3 py-1.5 text-xs"
    >
      {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
      {copied ? 'Copied' : 'Copy'}
    </button>
  )
}

export default function AIWritingCard({ writing }: { writing: AIWriting }) {
  return (
    <div className="card">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Wand2 className="h-5 w-5 text-brand-300" />
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
            AI Writing Assistant
          </h3>
        </div>
        <span className="rounded-full bg-white/5 px-2.5 py-1 text-[10px] font-medium text-slate-400 ring-1 ring-white/10">
          {writing.ai_generated ? 'Gemini-generated' : 'Smart template'}
        </span>
      </div>

      {writing.headline && (
        <div className="mt-4">
          <div className="mb-1.5 flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Improved Headline
            </span>
            <CopyButton text={writing.headline} />
          </div>
          <p className="rounded-xl bg-white/5 p-3 text-sm text-white ring-1 ring-white/10">
            {writing.headline}
          </p>
        </div>
      )}

      {writing.about && (
        <div className="mt-5">
          <div className="mb-1.5 flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Improved About Section
            </span>
            <CopyButton text={writing.about} />
          </div>
          <p className="whitespace-pre-line rounded-xl bg-white/5 p-3 text-sm leading-relaxed text-slate-200 ring-1 ring-white/10">
            {writing.about}
          </p>
        </div>
      )}
    </div>
  )
}
