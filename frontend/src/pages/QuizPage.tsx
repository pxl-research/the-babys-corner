import { useNavigate, useParams } from 'react-router-dom'
import { useEffect, useState } from 'react'
import Header from '../components/Header'
import ProgressDots from '../components/ProgressDots'
import { api } from '../api/client'
import { useSessionStore } from '../store/sessionStore'

const PROFILE_STEPS = 2
const TAG_STEPS = 4
const FIRST_TAG_STEP = PROFILE_STEPS + 1 // 3
const LAST_TAG_STEP = PROFILE_STEPS + TAG_STEPS // 6
const NOTE_STEP = PROFILE_STEPS + TAG_STEPS + 1 // 7
const TOTAL_STEPS = NOTE_STEP

export default function QuizPage() {
  const { step } = useParams<{ step: string }>()
  const navigate = useNavigate()
  const stepNum = parseInt(step || '1', 10)

  const {
    quizAnswers, setAnswer,
    optionalNote, setOptionalNote,
    profile, setProfile,
    transitionPhrase,
    quizConfig, setQuizConfig,
    tagConfig, setTagConfig,
    tagAnswers, setTagAnswer, setTagOutcome,
  } = useSessionStore()

  const [submitting, setSubmitting] = useState(false)
  // Fill a dot per answered profile question, per answered tag question, and once the
  // note step is reached — so progress never appears stuck on the back half of the quiz.
  const answeredProfile = quizAnswers.filter((a) => a !== undefined).length
  const answeredTags = Object.values(tagAnswers).filter((a) => a.length > 0).length
  const noteReached = stepNum >= NOTE_STEP ? 1 : 0
  const filledDots = answeredProfile + answeredTags + noteReached

  const isTagStep = stepNum >= FIRST_TAG_STEP && stepNum <= LAST_TAG_STEP

  useEffect(() => {
    if (!quizConfig) {
      api.getQuizConfig().then(setQuizConfig).catch(console.error)
    }
  }, [quizConfig, setQuizConfig])

  // Prefetch tag questions from the last profile step onward.
  useEffect(() => {
    if (stepNum >= PROFILE_STEPS && !tagConfig) {
      api.getTagConfig().then(setTagConfig).catch(console.error)
    }
  }, [stepNum, tagConfig, setTagConfig])

  // ── Steps 1–3: profile questions ─────────────────────────────────────────────

  function handleOptionSelect(index: number) {
    setAnswer(stepNum, index)
  }

  async function handleProfileNext() {
    if (stepNum < PROFILE_STEPS) {
      navigate(`/quiz/${stepNum + 1}`)
      return
    }
    // Last profile step → submit quiz, then go to first tag question.
    if (!profile) {
      setSubmitting(true)
      try {
        const answers = quizConfig!.questions.map((q, i) => ({
          question_id: q.id,
          option_index: quizAnswers[i] ?? 0,
        }))
        const result = await api.submitQuiz(answers)
        setProfile(result.profile as 'A' | 'B' | 'C', result.transition_phrase)
      } finally {
        setSubmitting(false)
      }
    }
    navigate(`/quiz/${FIRST_TAG_STEP}`)
  }

  function handleBack() {
    if (stepNum === 1) navigate('/')
    else navigate(`/quiz/${stepNum - 1}`)
  }

  // ── Steps 4–7: hidden tag questions ──────────────────────────────────────────

  const tagQuestion = tagConfig?.questions[stepNum - FIRST_TAG_STEP]

  function logTagCounts(answersMap: Record<string, number[]>) {
    const answers = (tagConfig?.questions ?? []).map((q) => ({
      question_id: q.id,
      option_indices: answersMap[q.id] ?? [],
    }))
    if (!import.meta.env.DEV) return
    api
      .tagQuizCount(answers)
      .then((c) =>
        console.debug(
          `[tag-quiz] strict(AND)=${c.strict_count} relaxed(OR)=${c.relaxed_count} total=${c.total_count}`
        )
      )
      .catch(() => {})
  }

  function toggleTagOption(qid: string, multi: boolean, index: number) {
    const current = tagAnswers[qid] ?? []
    const next = multi
      ? current.includes(index)
        ? current.filter((i) => i !== index)
        : [...current, index]
      : current.includes(index)
        ? []
        : [index]
    setTagAnswer(qid, next)
    logTagCounts({ ...tagAnswers, [qid]: next })
  }

  async function handleTagNext() {
    if (stepNum < LAST_TAG_STEP) {
      navigate(`/quiz/${stepNum + 1}`)
      return
    }
    setSubmitting(true)
    try {
      const answers = (tagConfig?.questions ?? []).map((q) => ({
        question_id: q.id,
        option_indices: tagAnswers[q.id] ?? [],
      }))
      const result = await api.submitTagQuiz(answers)
      setTagOutcome(result.match_mode, result.dropped_count)
      if (import.meta.env.DEV) {
        console.debug(
          `[tag-quiz] submit | mode=${result.match_mode} strict(AND)=${result.strict_count} ` +
            `dropped=${result.dropped_count} -> ${result.stroller_count} strollers`
        )
      }
      navigate(`/quiz/${NOTE_STEP}`)
    } finally {
      setSubmitting(false)
    }
  }

  // ── Step 8: optional note ────────────────────────────────────────────────────

  async function handleNoteSubmit(note: string) {
    if (submitting) return
    setSubmitting(true)
    try {
      await api.saveNote(note)
      navigate('/transition')
    } finally {
      setSubmitting(false)
    }
  }

  // ── Loading guard ────────────────────────────────────────────────────────────

  if (!quizConfig) {
    return (
      <div className="min-h-screen bg-cream flex items-center justify-center">
        <p className="text-ink/70">Laden…</p>
      </div>
    )
  }

  // Step 8: optional note
  if (stepNum === NOTE_STEP) {
    const noteConfig = quizConfig.optional_note

    if (submitting) {
      return (
        <div className="min-h-screen bg-cream text-ink font-sans flex flex-col items-center justify-center gap-6 px-6">
          {transitionPhrase && (
            <p className="font-display text-2xl font-bold text-ink text-center max-w-md">
              {transitionPhrase}
            </p>
          )}
          <div className="flex gap-2">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="w-3 h-3 rounded-full bg-brand animate-bounce"
                style={{ animationDelay: `${i * 0.15}s` }}
              />
            ))}
          </div>
          <p className="font-display text-xl font-bold text-ink text-center">
            We zoeken de beste matches voor jullie…
          </p>
          <p className="text-sm text-ink/70 text-center max-w-xs">
            We vergelijken jullie wensen met ons volledige assortiment. Dit duurt even.
          </p>
        </div>
      )
    }

    return (
      <div className="min-h-screen bg-cream text-ink font-sans">
        <Header />
        <div className="max-w-lg mx-auto px-6 py-8">
          <ProgressDots total={TOTAL_STEPS} current={NOTE_STEP} filled={filledDots} />
          <p className="font-display text-xl font-bold text-ink mt-6 mb-1">
            {noteConfig.text} <span className="text-ink/70 font-normal text-base">(optioneel)</span>
          </p>
          <p className="text-sm text-ink/70 mb-4">Geen extra info? Sla deze stap gerust over.</p>
          <textarea
            value={optionalNote}
            onChange={(e) => setOptionalNote(e.target.value)}
            maxLength={noteConfig.max_length}
            rows={5}
            placeholder="Schrijf hier jullie extra info…"
            className="w-full border-2 border-muted rounded-card p-4 bg-white text-ink resize-none focus:border-brand outline-none"
          />
          <div className="flex flex-col gap-3 mt-6">
            <button
              onClick={() => handleNoteSubmit(optionalNote)}
              className="bg-brand text-ink rounded-btn px-6 py-3 font-medium"
            >
              {noteConfig.continue_label}
            </button>
            <button onClick={() => navigate(`/quiz/${LAST_TAG_STEP}`)} className="border border-brand text-brand-dark rounded-btn px-6 py-3 font-medium">
              Terug
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Steps 4–7: tag questions (the tags themselves are never shown)
  if (isTagStep) {
    if (!tagConfig || !tagQuestion) {
      return (
        <div className="min-h-screen bg-cream flex items-center justify-center">
          <p className="text-ink/70">Laden…</p>
        </div>
      )
    }
    const selected = tagAnswers[tagQuestion.id] ?? []

    return (
      <div className="min-h-screen bg-cream text-ink font-sans">
        <Header />
        <div className="max-w-lg mx-auto px-6 py-8">
          <ProgressDots total={TOTAL_STEPS} current={stepNum} filled={filledDots} />
          {stepNum === FIRST_TAG_STEP && (
            <p className="text-ink/80 mt-6 mb-2">
              Kinderwagens zijn onze specialiteit — en voor elk gezin is er het perfecte
              model. Ik stel je een paar gerichte vragen, zodat ik je precies kan tonen
              wat bij jullie past.
            </p>
          )}
          <p className="font-display text-xl font-bold text-ink mt-6 mb-2">{tagQuestion.text}</p>
          <p className="text-xs text-ink/70 mb-6">
            {tagQuestion.multi ? 'Meerdere antwoorden mogelijk' : 'Kies één antwoord'} — of sla over
          </p>
          <div className="flex flex-col gap-2">
            {tagQuestion.options.map((opt) => {
              const isSelected = selected.includes(opt.index)
              return (
                <button
                  key={opt.index}
                  onClick={() => toggleTagOption(tagQuestion.id, tagQuestion.multi, opt.index)}
                  className={[
                    'border-2 rounded-card p-4 w-full text-left transition-colors',
                    isSelected ? 'border-brand bg-brand/10' : 'border-muted hover:border-brand/50',
                  ].join(' ')}
                >
                  {opt.text}
                </button>
              )
            })}
          </div>
          <div className="flex flex-col gap-3 mt-8">
            <button
              onClick={handleTagNext}
              disabled={submitting}
              className="bg-brand text-ink rounded-btn px-6 py-3 font-medium disabled:opacity-50"
            >
              {submitting ? 'Bezig…' : stepNum === LAST_TAG_STEP ? 'Bekijk aanbevelingen' : 'Volgende'}
            </button>
            <button onClick={handleBack} className="border border-brand text-brand-dark rounded-btn px-6 py-3 font-medium">
              Terug
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Steps 1–3: profile questions
  const question = quizConfig.questions[stepNum - 1]
  const selectedOption = quizAnswers[stepNum - 1] ?? -1

  return (
    <div className="min-h-screen bg-cream text-ink font-sans">
      <Header />
      <div className="max-w-lg mx-auto px-6 py-8">
        <ProgressDots total={TOTAL_STEPS} current={stepNum} filled={filledDots} />
        <p className="font-display text-xl font-bold text-ink mt-6 mb-6">{question?.text}</p>
        <div className="flex flex-col gap-3">
          {question?.options.map((opt) => (
            <button
              key={opt.index}
              onClick={() => handleOptionSelect(opt.index)}
              className={[
                'border-2 rounded-card p-4 w-full text-left transition-colors',
                selectedOption === opt.index
                  ? 'border-brand bg-brand/10'
                  : 'border-muted hover:border-brand/50',
              ].join(' ')}
            >
              {opt.text}
            </button>
          ))}
        </div>
        <div className="flex flex-col gap-3 mt-8">
          <button
            onClick={handleProfileNext}
            disabled={selectedOption === -1 || submitting}
            className="bg-brand text-ink rounded-btn px-6 py-3 font-medium disabled:opacity-50"
          >
            {submitting ? 'Bezig…' : 'Volgende'}
          </button>
          {stepNum > 1 && (
            <button onClick={handleBack} className="border border-brand text-brand-dark rounded-btn px-6 py-3 font-medium">
              Terug
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
