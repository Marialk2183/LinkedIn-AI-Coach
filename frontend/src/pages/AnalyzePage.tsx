import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FileText, Link2, Upload, AlertCircle, Sparkles, FileCheck2, X, Download } from 'lucide-react'
import Loader from '../components/Loader'
import { analyzeProfile, uploadProfile, fetchSource, apiErrorMessage } from '../api/client'
import type { SourceType } from '../types/analysis'

type Tab = SourceType

const SAMPLE = `Jane Doe
MCA Student | Aspiring Data Scientist
About
Aspiring data scientist passionate about machine learning and analytics. I enjoy building models and turning data into decisions. Currently completing my Master of Computer Applications.
Experience
Data Science Intern at Acme (2023 - 2024)
- Built churn prediction models in Python and scikit-learn
Education
MCA, XYZ University
Skills
Python, SQL, Machine Learning, Pandas, NumPy, Data Visualization, Statistics
Certifications
Google Data Analytics Certificate
Projects
Customer churn prediction using scikit-learn
500+ connections`

const ACCEPT = '.pdf,.txt,.md,.zip'
const MAX_MB = 10

export default function AnalyzePage() {
  const [tab, setTab] = useState<Tab>('text')
  const [text, setText] = useState('')
  const [url, setUrl] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [importing, setImporting] = useState(false)
  const [imported, setImported] = useState('')
  const [error, setError] = useState('')
  const fileInput = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()

  async function importFromUrl() {
    setError('')
    setImported('')
    if (!url.trim()) {
      setError('Enter a GitHub, portfolio, or job-posting URL to import.')
      return
    }
    setImporting(true)
    try {
      const src = await fetchSource(url.trim())
      setText(src.text)
      setTab('text')
      setImported(`Imported ${src.char_count.toLocaleString()} characters from ${src.title}. Review and edit below, then analyze.`)
    } catch (e) {
      setError(apiErrorMessage(e))
    } finally {
      setImporting(false)
    }
  }

  function pickFile(f: File | null) {
    setError('')
    if (!f) return
    if (f.size > MAX_MB * 1024 * 1024) {
      setError(`That file is larger than ${MAX_MB} MB.`)
      return
    }
    setFile(f)
  }

  async function submit() {
    setError('')
    if (tab === 'text' && !text.trim()) {
      setError('Paste your LinkedIn profile content to analyze.')
      return
    }
    if (tab === 'export' && !file) {
      setError('Choose a PDF, .txt, or LinkedIn data-export .zip to upload.')
      return
    }
    setLoading(true)
    try {
      const result =
        tab === 'export' && file
          ? await uploadProfile(file)
          : await analyzeProfile({ source_type: 'text', profile_text: text || undefined })
      navigate('/dashboard', { state: { result } })
    } catch (e) {
      setError(apiErrorMessage(e))
      setLoading(false)
    }
  }

  if (loading) return <Loader />

  const tabs: { id: Tab; label: string; icon: typeof FileText }[] = [
    { id: 'text', label: 'Paste Text', icon: FileText },
    { id: 'url', label: 'Import from URL', icon: Link2 },
    { id: 'export', label: 'Upload File', icon: Upload },
  ]

  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6 lg:px-8">
      <div className="text-center">
        <h1 className="text-3xl font-extrabold text-white sm:text-4xl">
          Analyze your <span className="gradient-text">profile</span>
        </h1>
        <p className="mx-auto mt-3 max-w-xl text-slate-400">
          Paste your content, import from GitHub / a portfolio / a job post, or upload a PDF or LinkedIn data export. We never store credentials and don't scrape LinkedIn.
        </p>
      </div>

      <div className="mt-8 flex gap-2">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => {
              setTab(t.id)
              setError('')
            }}
            className={`flex flex-1 items-center justify-center gap-2 rounded-xl border px-3 py-2.5 text-sm font-medium transition-colors ${
              tab === t.id
                ? 'border-brand-500/40 bg-brand-500/15 text-brand-200'
                : 'border-white/10 bg-white/5 text-slate-300 hover:bg-white/10'
            }`}
          >
            <t.icon className="h-4 w-4" />
            {t.label}
          </button>
        ))}
      </div>

      <div className="mt-5 card">
        {tab === 'url' && (
          <div>
            <div className="flex gap-2">
              <input
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && importFromUrl()}
                placeholder="https://github.com/your-name  ·  your-portfolio.com  ·  a job posting"
                className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-brand-500/50 focus:outline-none"
              />
              <button
                onClick={importFromUrl}
                disabled={importing}
                className="btn-primary shrink-0 disabled:opacity-60"
              >
                <Download className="h-4 w-4" /> {importing ? 'Importing…' : 'Import'}
              </button>
            </div>
            <p className="mt-3 text-xs text-slate-400">
              Pulls public text from <span className="text-slate-200">GitHub</span> (official API),
              a portfolio site, or a job posting into the editor. We never scrape LinkedIn — for
              that, use <button onClick={() => setTab('export')} className="text-brand-300 hover:text-brand-200">Upload File</button>.
            </p>
          </div>
        )}

        {tab === 'export' ? (
          <div>
            <input
              ref={fileInput}
              type="file"
              accept={ACCEPT}
              className="hidden"
              onChange={(e) => pickFile(e.target.files?.[0] ?? null)}
            />
            {file ? (
              <div className="flex items-center gap-3 rounded-xl border border-brand-500/30 bg-brand-500/10 px-4 py-4">
                <FileCheck2 className="h-6 w-6 shrink-0 text-brand-300" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-white">{file.name}</p>
                  <p className="text-xs text-slate-400">{(file.size / 1024).toFixed(0)} KB</p>
                </div>
                <button
                  onClick={() => setFile(null)}
                  className="rounded-lg p-1.5 text-slate-400 hover:bg-white/10 hover:text-white"
                  aria-label="Remove file"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            ) : (
              <button
                onClick={() => fileInput.current?.click()}
                onDragOver={(e) => {
                  e.preventDefault()
                  setDragging(true)
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={(e) => {
                  e.preventDefault()
                  setDragging(false)
                  pickFile(e.dataTransfer.files?.[0] ?? null)
                }}
                className={`flex w-full flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed px-6 py-14 text-center transition-colors ${
                  dragging
                    ? 'border-brand-500/60 bg-brand-500/10'
                    : 'border-white/15 bg-white/5 hover:bg-white/10'
                }`}
              >
                <Upload className="h-8 w-8 text-brand-300" />
                <span className="text-sm font-medium text-slate-200">
                  Drop a file here, or click to browse
                </span>
                <span className="text-xs text-slate-500">
                  PDF resume · .txt · LinkedIn data-export .zip · max {MAX_MB} MB
                </span>
              </button>
            )}
            <p className="mt-3 text-xs text-slate-500">
              Tip: export your data from LinkedIn → Settings → Data privacy → “Get a copy of your data”, or use
              “Save to PDF” from your profile’s More menu.
            </p>
          </div>
        ) : tab === 'text' ? (
          <>
            {imported && (
              <p className="mb-3 flex items-start gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-200">
                <FileCheck2 className="mt-0.5 h-4 w-4 shrink-0" /> {imported}
              </p>
            )}
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={12}
              placeholder="Paste your full LinkedIn profile text here (headline, about, experience, skills, etc.)"
              className="w-full resize-y rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-200 placeholder:text-slate-500 focus:border-brand-500/50 focus:outline-none"
            />
            <div className="mt-3">
              <button onClick={() => setText(SAMPLE)} className="text-xs text-brand-300 hover:text-brand-200">
                Load a sample profile
              </button>
            </div>
          </>
        ) : null}

        {tab !== 'url' && (
          <div className="mt-4 flex justify-end">
            <button onClick={submit} className="btn-primary">
              <Sparkles className="h-4 w-4" /> Analyze Profile
            </button>
          </div>
        )}
        {error && (
          <p className="mt-4 flex items-center gap-2 text-sm text-rose-400">
            <AlertCircle className="h-4 w-4 shrink-0" /> {error}
          </p>
        )}
      </div>
    </div>
  )
}
