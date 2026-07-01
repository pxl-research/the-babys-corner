import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { StrollerItem, QuizQuestion, OptionalNoteConfig, TagConfig, RecommendationTier, CategoryConfig } from '../api/client'

export type AppStatus =
  | 'idle'
  | 'quiz'
  | 'transition'
  | 'recommendations'
  | 'shortlist'
  | 'handoff'
  | 'completed'

interface SessionStore {
  sessionId: string | null
  sessionCode: string | null
  source: 'store' | 'home'
  quizAnswers: number[]
  optionalNote: string
  profile: 'A' | 'B' | 'C' | null
  transitionPhrase: string | null
  recommendations: StrollerItem[][]
  recoTiers: RecommendationTier[]
  currentBatch: number
  strollerFavorites: string[]
  accessoryFavorites: string[]
  status: AppStatus
  handoffAt: string | null
  // Email is deferred: the backend still tracks status, but no client UI surfaces it.
  // Do not wire new UI to emailStatus — see UX_IMPLEMENTATION_PLAN.md Phase A.
  emailStatus: 'not_sent' | 'pending' | 'sent' | 'failed'
  favoritesAdaptationActive: boolean
  quizConfig: { questions: QuizQuestion[]; optional_note: OptionalNoteConfig } | null
  tagConfig: TagConfig | null
  tagAnswers: Record<string, number[]>
  tagMatchMode: string | null
  droppedTagCount: number
  categoryConfig: CategoryConfig | null
  activeCategory: string | null
  selectedCategories: string[]
  tagAnswersByCategory: Record<string, Record<string, number[]>>

  setSource: (source: 'store' | 'home') => void
  setSession: (id: string, code: string) => void
  setAnswer: (step: number, optionIndex: number) => void
  setOptionalNote: (note: string) => void
  setProfile: (profile: 'A' | 'B' | 'C', phrase: string) => void
  addBatch: (products: StrollerItem[]) => void
  setRecoTiers: (tiers: RecommendationTier[]) => void
  setFavorites: (strollers: string[], accessories: string[]) => void
  setStatus: (status: AppStatus) => void
  setHandoff: (code: string, at: string) => void
  setEmailStatus: (status: 'not_sent' | 'pending' | 'sent' | 'failed') => void
  setFavoritesAdaptation: (active: boolean) => void
  setQuizConfig: (config: { questions: QuizQuestion[]; optional_note: OptionalNoteConfig }) => void
  setTagConfig: (config: TagConfig) => void
  setTagAnswer: (questionId: string, indices: number[]) => void
  setTagOutcome: (matchMode: string, droppedCount: number) => void
  setCategoryConfig: (config: CategoryConfig) => void
  addSelectedCategory: (id: string) => void
  startCategory: (id: string) => void
  reset: () => void
}

const initial = {
  sessionId: null,
  sessionCode: null,
  source: 'home' as const,
  quizAnswers: [],
  optionalNote: '',
  profile: null,
  transitionPhrase: null,
  recommendations: [],
  recoTiers: [],
  currentBatch: 0,
  strollerFavorites: [],
  accessoryFavorites: [],
  status: 'idle' as const,
  handoffAt: null,
  emailStatus: 'not_sent' as const,
  favoritesAdaptationActive: false,
  quizConfig: null,
  tagConfig: null,
  tagAnswers: {} as Record<string, number[]>,
  tagMatchMode: null,
  droppedTagCount: 0,
  categoryConfig: null,
  activeCategory: null,
  selectedCategories: [],
  tagAnswersByCategory: {} as Record<string, Record<string, number[]>>,
}

export const useSessionStore = create<SessionStore>()(
  persist(
    (set) => ({
      ...initial,

      setSource: (source) => set({ source }),
      setSession: (sessionId, sessionCode) => set({ sessionId, sessionCode }),
      setAnswer: (step, optionIndex) =>
        set((s) => {
          const answers = [...s.quizAnswers]
          answers[step - 1] = optionIndex
          return { quizAnswers: answers }
        }),
      setOptionalNote: (optionalNote) => set({ optionalNote }),
      setProfile: (profile, transitionPhrase) => set({ profile, transitionPhrase }),
      addBatch: (products) =>
        set((s) => ({
          recommendations: [...s.recommendations, products],
          currentBatch: s.currentBatch + 1,
        })),
      setRecoTiers: (recoTiers) => set({ recoTiers }),
      setFavorites: (strollerFavorites, accessoryFavorites) =>
        set({ strollerFavorites, accessoryFavorites }),
      setStatus: (status) => set({ status }),
      setHandoff: (sessionCode, handoffAt) => set({ sessionCode, handoffAt }),
      setEmailStatus: (emailStatus) => set({ emailStatus }),
      setFavoritesAdaptation: (favoritesAdaptationActive) => set({ favoritesAdaptationActive }),
      setQuizConfig: (quizConfig) => set({ quizConfig }),
      setTagConfig: (tagConfig) => set({ tagConfig }),
      setTagAnswer: (questionId, indices) =>
        set((s) => {
          const byCategory = s.activeCategory
            ? {
                tagAnswersByCategory: {
                  ...s.tagAnswersByCategory,
                  [s.activeCategory]: {
                    ...(s.tagAnswersByCategory[s.activeCategory] ?? {}),
                    [questionId]: indices,
                  },
                },
              }
            : {}
          return { tagAnswers: { ...s.tagAnswers, [questionId]: indices }, ...byCategory }
        }),
      setTagOutcome: (tagMatchMode, droppedTagCount) => set({ tagMatchMode, droppedTagCount }),
      setCategoryConfig: (categoryConfig) => set({ categoryConfig }),
      addSelectedCategory: (id) =>
        set((s) => ({
          selectedCategories: s.selectedCategories.includes(id)
            ? s.selectedCategories
            : [...s.selectedCategories, id],
        })),
      startCategory: (id) =>
        set((s) => ({
          activeCategory: id,
          tagAnswers: s.tagAnswersByCategory[id] ?? {},
          recommendations: [],
          currentBatch: 0,
          recoTiers: [],
          tagMatchMode: null,
          droppedTagCount: 0,
          favoritesAdaptationActive: false,
        })),
      reset: () =>
        set((s) => ({
          ...initial,
          strollerFavorites: s.strollerFavorites,
          accessoryFavorites: s.accessoryFavorites,
        })),
    }),
    { name: 'babys-corner-session' }
  )
)
