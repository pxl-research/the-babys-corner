import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { StrollerItem, QuizQuestion, OptionalNoteConfig } from '../api/client'

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
  currentBatch: number
  strollerFavorites: string[]
  accessoryFavorites: string[]
  status: AppStatus
  handoffAt: string | null
  emailStatus: 'not_sent' | 'pending' | 'sent' | 'failed'
  favoritesAdaptationActive: boolean
  quizConfig: { questions: QuizQuestion[]; optional_note: OptionalNoteConfig } | null

  setSource: (source: 'store' | 'home') => void
  setSession: (id: string, code: string) => void
  setAnswer: (step: number, optionIndex: number) => void
  setOptionalNote: (note: string) => void
  setProfile: (profile: 'A' | 'B' | 'C', phrase: string) => void
  addBatch: (products: StrollerItem[]) => void
  setFavorites: (strollers: string[], accessories: string[]) => void
  setStatus: (status: AppStatus) => void
  setHandoff: (code: string, at: string) => void
  setEmailStatus: (status: 'not_sent' | 'pending' | 'sent' | 'failed') => void
  setFavoritesAdaptation: (active: boolean) => void
  setQuizConfig: (config: { questions: QuizQuestion[]; optional_note: OptionalNoteConfig }) => void
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
  currentBatch: 0,
  strollerFavorites: [],
  accessoryFavorites: [],
  status: 'idle' as const,
  handoffAt: null,
  emailStatus: 'not_sent' as const,
  favoritesAdaptationActive: false,
  quizConfig: null,
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
      setFavorites: (strollerFavorites, accessoryFavorites) =>
        set({ strollerFavorites, accessoryFavorites }),
      setStatus: (status) => set({ status }),
      setHandoff: (sessionCode, handoffAt) => set({ sessionCode, handoffAt }),
      setEmailStatus: (emailStatus) => set({ emailStatus }),
      setFavoritesAdaptation: (favoritesAdaptationActive) => set({ favoritesAdaptationActive }),
      setQuizConfig: (quizConfig) => set({ quizConfig }),
      reset: () => set(initial),
    }),
    { name: 'babys-corner-session' }
  )
)
