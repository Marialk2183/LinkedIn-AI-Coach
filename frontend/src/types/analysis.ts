// Mirrors the backend AnalysisResponse contract (models/schemas.py).

export type SourceType = 'url' | 'text' | 'export'

export interface Scores {
  overall: number
  completeness: number
  technical: number
  recruiter: number
  networking: number
  career_readiness: number
  ats: number
  leadership: number
}

export interface MetricBreakdown {
  score: number
  components: Record<string, number>
}

export interface RecommendationItem {
  category: string
  content: string
  impact_points?: number | null
  example?: string | null
}

export interface CareerMatch {
  role: string
  match_pct: number
  matched_skills: string[]
  missing_skills: string[]
}

export interface AIWriting {
  headline: string | null
  about: string | null
  ai_generated: boolean
}

export interface ParsedSummary {
  name: string | null
  headline: string
  skills_count: number
  certifications_count: number
  projects_count: number
  experience_years: number
  connections: number | null
  followers: number | null
}

export interface AnalysisResponse {
  analysis_id: number | null
  source_type: SourceType
  scores: Scores
  breakdown: Record<string, MetricBreakdown>
  ml_used: boolean
  parsed: ParsedSummary
  strengths: string[]
  weaknesses: string[]
  recommendations: RecommendationItem[]
  career_predictions: CareerMatch[]
  ai_writing: AIWriting
}

export interface AnalyzeRequest {
  source_type: SourceType
  profile_url?: string
  profile_text?: string
}

export type FetchKind = 'github' | 'web'

export interface FetchResponse {
  url: string
  kind: FetchKind
  title: string
  text: string
  char_count: number
  metadata: Record<string, string | number>
}
