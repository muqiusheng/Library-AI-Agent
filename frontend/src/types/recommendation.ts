export interface HoldingCard {
  id: string
  call_number: string | null
  collection_location: string | null
  current_location: string | null
  shelf_number: string | null
  book_status: string
  circulation_status: string
}

export interface ScoreBreakdown {
  goal: number
  difficulty: number
  major: number
  interest: number
  semantic: number
  availability: number
}

export interface RecommendationCardData {
  book_id: string
  title: string
  responsible_person: string | null
  isbn: string | null
  publisher: string | null
  publication_year: number | null
  description: string | null
  topics: string[]
  difficulty: string
  learning_stage: string
  total_score: number
  scores: ScoreBreakdown
  reason: string
  holdings_count: number
  available_count: number
  holdings: HoldingCard[]
}

export interface RecommendationSetData {
  id: string
  query: string
  summary: string
  created_at: string
  items: RecommendationCardData[]
}
