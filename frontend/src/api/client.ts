export interface QuizOption {
  index: number
  text: string
}

export interface QuizQuestion {
  id: number
  text: string
  options: QuizOption[]
}

export interface OptionalNoteConfig {
  text: string
  skip_label: string
  continue_label: string
  max_length: number
}

export interface QuizConfig {
  questions: QuizQuestion[]
  optional_note: OptionalNoteConfig
}

export interface AccessoryItem {
  id: string
  name: string
  brand: string
  price: number
  description: string
  image_url: string
  availability: string
  is_available: boolean
}

export interface StrollerItem {
  id: string
  name: string
  brand: string
  price: number
  description: string
  formatted_description?: string
  image_url: string
  availability: string
  is_available: boolean
  key_features: string
  cross_sell_items: AccessoryItem[]
  show_cross_sell_chips: boolean
}

export interface RecommendationBatch {
  batch: number
  favorites_adaptation_active: boolean
  products: StrollerItem[]
}

export interface SessionState {
  session_id: string
  session_code: string
  source: string
  status: string
  started_at: string
  quiz_submitted_at: string | null
  handoff_at: string | null
  quiz_answers: object[]
  optional_note: string | null
  profile: string | null
  transition_phrase: string | null
  shown_products: string[][]
  stroller_favorites: string[]
  accessory_favorites: string[]
  email_status: string
  favorites_adaptation_active: boolean
  talking_points: string[] | null
}

export interface BrandCollections {
  brand: string
  collections: string[]
}

export interface FilterTagsResponse {
  brands: string[]
}

export interface FilterBrandsResponse {
  brands: BrandCollections[]
}

export interface FilterCollectionsResponse {
  stroller_count: number
  accessory_count: number
}

export interface CollectionSelection {
  brand: string
  collection: string | null
}

export interface HandoffResponse {
  session_code: string
  handoff_at: string
  email_status: string
}

export interface StaffSession {
  session_id: string
  session_code: string
  source: string
  status: string
  started_at: string
  handoff_at: string | null
  profile: string | null
  email_status: string | null
}

export interface StaffSessionDetail extends StaffSession {
  quiz_answers: object[]
  optional_note: string | null
  shown_products: string[][]
  stroller_favorites: string[]
  accessory_favorites: string[]
  talking_points: string[] | null
  email_failed_warning: boolean
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(path, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }))
    throw Object.assign(new Error(err.detail || resp.statusText), { status: resp.status })
  }
  return resp.json()
}

export const api = {
  createSession: (source: string) =>
    request<{ session_id: string; session_code: string }>(`/api/sessions?source=${source}`, { method: 'POST' }),

  getQuizConfig: () => request<QuizConfig>('/api/sessions/quiz-config'),

  getSession: () => request<SessionState>('/api/sessions/current'),

  submitQuiz: (answers: { question_id: number; option_index: number }[]) =>
    request<{ profile: string; transition_phrase: string }>('/api/sessions/current/quiz', {
      method: 'POST',
      body: JSON.stringify({ answers, optional_note: '' }),
    }),

  getTags: () => request<{ tags: string[] }>('/api/filters/tags'),

  filterTags: (tags: string[]) =>
    request<FilterTagsResponse>('/api/sessions/current/filters/tags', {
      method: 'POST',
      body: JSON.stringify({ tags }),
    }),

  filterBrands: (brands: string[]) =>
    request<FilterBrandsResponse>('/api/sessions/current/filters/brands', {
      method: 'POST',
      body: JSON.stringify({ brands }),
    }),

  filterCollections: (selections: CollectionSelection[]) =>
    request<FilterCollectionsResponse>('/api/sessions/current/filters/collections', {
      method: 'POST',
      body: JSON.stringify({ selections }),
    }),

  saveNote: (note: string) =>
    request<{ note: string | null }>('/api/sessions/current/note', {
      method: 'POST',
      body: JSON.stringify({ note }),
    }),

  getRecommendations: (batch: number) =>
    request<RecommendationBatch>(`/api/sessions/current/recommendations?batch=${batch}`),

  toggleFavorite: (item_id: string, item_type: 'stroller' | 'accessory') =>
    request<{ stroller_favorites: string[]; accessory_favorites: string[] }>(
      '/api/sessions/current/favorites',
      { method: 'POST', body: JSON.stringify({ item_id, item_type }) }
    ),

  handoff: () =>
    request<HandoffResponse>('/api/sessions/current/handoff', { method: 'POST' }),

  abandon: () => request<void>('/api/sessions/current/abandon', { method: 'POST' }),

  getStaffSessions: (params: Record<string, string>, credentials: string) =>
    request<StaffSession[]>(`/api/staff/sessions?${new URLSearchParams(params)}`, {
      headers: { Authorization: `Basic ${credentials}` },
    }),

  getStaffSessionDetail: (code: string, credentials: string) =>
    request<StaffSessionDetail>(`/api/staff/sessions/${code}`, {
      headers: { Authorization: `Basic ${credentials}` },
    }),

  getAdminSessions: (params: Record<string, string>, credentials: string) =>
    request<StaffSession[]>(`/api/admin/sessions?${new URLSearchParams(params)}`, {
      headers: { Authorization: `Basic ${credentials}` },
    }),

  getAdminSessionDetail: (code: string, credentials: string) =>
    request<StaffSessionDetail>(`/api/admin/sessions/${code}`, {
      headers: { Authorization: `Basic ${credentials}` },
    }),

  exportAdmin: (credentials: string) =>
    fetch('/api/admin/sessions/export', {
      headers: { Authorization: `Basic ${credentials}` },
    }),
}
