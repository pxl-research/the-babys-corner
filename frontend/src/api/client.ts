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

export interface TagQuestion {
  id: string
  text: string
  subtitle: string | null
  multi: boolean
  options: QuizOption[]
}

export interface TagConfig {
  questions: TagQuestion[]
}

export interface TagAnswer {
  question_id: string
  option_indices: number[]
}

export interface TagQuizResponse {
  stroller_count: number
  accessory_count: number
  match_mode: string
  strict_count: number
  dropped_count: number
}

export interface TagCountResponse {
  strict_count: number
  relaxed_count: number
  total_count: number
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
  reason?: string
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
  variant_count?: number
  variant_ids?: string[]
}

export interface NamedItem {
  id: string
  name: string
  brand: string
  image_url: string
  price?: number | null
}

export interface ShortlistItem {
  id: string
  name: string
  brand: string
  price: number
  image_url: string
  availability: string
  is_available: boolean
}

export interface FavoriteItemsResponse {
  strollers: ShortlistItem[]
  accessories: ShortlistItem[]
}

export interface RecommendationTier {
  label: string
  start_index: number
}

export interface RecommendationBatch {
  batch: number
  favorites_adaptation_active: boolean
  products: StrollerItem[]
  tiers: RecommendationTier[]
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
  shown_products_named: NamedItem[][]
  stroller_favorites_named: NamedItem[]
  accessory_favorites_named: NamedItem[]
  email_status: string
  favorites_adaptation_active: boolean
  contact_name: string | null
  contact_surname: string | null
  contact_email: string | null
  talking_points: string[] | null
}

export interface ContactDetails {
  name?: string
  surname?: string
  email?: string
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
  tag_answers: object[]
  optional_note: string | null
  shown_products: string[][]
  stroller_favorites: string[]
  accessory_favorites: string[]
  shown_products_named: NamedItem[][]
  stroller_favorites_named: NamedItem[]
  accessory_favorites_named: NamedItem[]
  talking_points: string[] | null
  email_failed_warning: boolean
  contact_name: string | null
  contact_surname: string | null
  contact_email: string | null
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

  getTagConfig: () => request<TagConfig>('/api/sessions/tag-config'),

  submitTagQuiz: (answers: TagAnswer[]) =>
    request<TagQuizResponse>('/api/sessions/current/tag-quiz', {
      method: 'POST',
      body: JSON.stringify({ answers }),
    }),

  tagQuizCount: (answers: TagAnswer[]) =>
    request<TagCountResponse>('/api/sessions/current/tag-quiz/count', {
      method: 'POST',
      body: JSON.stringify({ answers }),
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

  getFavoriteItems: () =>
    request<FavoriteItemsResponse>('/api/sessions/current/favorites/items'),

  handoff: (contact?: ContactDetails) =>
    request<HandoffResponse>('/api/sessions/current/handoff', {
      method: 'POST',
      body: JSON.stringify(contact ?? {}),
    }),

  abandon: () => request<void>('/api/sessions/current/abandon', { method: 'POST' }),

  // Auth: credentials are sent once to /login, which sets an HttpOnly cookie.
  // Later requests rely on that cookie (request() already sends credentials).
  login: (username: string, password: string) =>
    request<{ role: string }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),

  logout: () => request<{ status: string }>('/api/auth/logout', { method: 'POST' }),

  authMe: () => request<{ role: string }>('/api/auth/me'),

  getStaffSessions: (params: Record<string, string>) =>
    request<StaffSession[]>(`/api/staff/sessions?${new URLSearchParams(params)}`),

  getStaffSessionDetail: (code: string) =>
    request<StaffSessionDetail>(`/api/staff/sessions/${code}`),

  getAdminSessions: (params: Record<string, string>) =>
    request<StaffSession[]>(`/api/admin/sessions?${new URLSearchParams(params)}`),

  getAdminSessionDetail: (code: string) =>
    request<StaffSessionDetail>(`/api/admin/sessions/${code}`),

  exportAdmin: () => fetch('/api/admin/sessions/export', { credentials: 'include' }),
}
