import { useNavigate, useParams } from 'react-router-dom'
import { useEffect, useState } from 'react'
import Header from '../components/Header'
import ProgressDots from '../components/ProgressDots'
import { api } from '../api/client'
import { useSessionStore } from '../store/sessionStore'

export default function QuizPage() {
  const { step } = useParams<{ step: string }>()
  const navigate = useNavigate()
  const stepNum = parseInt(step || '1', 10)

  const { quizAnswers, setAnswer, optionalNote, setOptionalNote, setProfile, quizConfig, setQuizConfig } =
    useSessionStore()

  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!quizConfig) {
      api.getQuizConfig().then(setQuizConfig).catch(console.error)
    }
  }, [quizConfig, setQuizConfig])

  const question = quizConfig?.questions[stepNum - 1]
  const selectedOption = quizAnswers[stepNum - 1] ?? -1
  const filledDots = quizAnswers.filter((a) => a !== undefined).length

  function handleOptionSelect(index: number) {
    setAnswer(stepNum, index)
  }

  function handleNext() {
    if (stepNum < 5) navigate(`/quiz/${stepNum + 1}`)
    else navigate('/quiz/6')
  }

  function handleBack() {
    if (stepNum === 1) navigate('/')
    else navigate(`/quiz/${stepNum - 1}`)
  }

  async function handleSubmit(note: string) {
    if (submitting) return
    setSubmitting(true)
    try {
      const answers = quizConfig!.questions.map((q, i) => ({
        question_id: q.id,
        option_index: quizAnswers[i] ?? 0,
      }))
      const result = await api.submitQuiz(answers, note)
      setProfile(result.profile as 'A' | 'B' | 'C', result.transition_phrase)
      navigate('/transition')
    } finally {
      setSubmitting(false)
    }
  }

  if (!quizConfig) {
    return (
      <div className="min-h-screen bg-cream flex items-center justify-center">
        <p className="text-ink/50">Laden…</p>
      </div>
    )
  }

  // Step 6: optional note
  if (stepNum === 6) {
    const noteConfig = quizConfig.optional_note
    return (
      <div className="min-h-screen bg-cream text-ink font-sans">
        <Header />
        <div className="max-w-lg mx-auto px-6 py-8">
          <ProgressDots total={6} current={6} filled={filledDots} />
          <p className="font-display text-xl font-bold text-ink mt-6 mb-4">{noteConfig.text}</p>
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
              onClick={() => handleSubmit(optionalNote)}
              disabled={submitting}
              className="bg-brand text-white rounded-btn px-6 py-3 font-medium disabled:opacity-50"
            >
              {submitting ? 'Bezig…' : noteConfig.continue_label}
            </button>
            <button
              onClick={() => handleSubmit('')}
              disabled={submitting}
              className="border border-brand text-brand rounded-btn px-6 py-3 font-medium disabled:opacity-50"
            >
              {noteConfig.skip_label}
            </button>
            <button
              onClick={handleBack}
              disabled={submitting}
              className="border border-brand text-brand rounded-btn px-6 py-3 font-medium"
            >
              Terug
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Steps 1-5: scoring questions
  return (
    <div className="min-h-screen bg-cream text-ink font-sans">
      <Header />
      <div className="max-w-lg mx-auto px-6 py-8">
        <ProgressDots total={6} current={stepNum} filled={filledDots} />
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
            onClick={handleNext}
            disabled={selectedOption === -1}
            className="bg-brand text-white rounded-btn px-6 py-3 font-medium disabled:opacity-50"
          >
            {stepNum === 5 ? 'Bevestig' : 'Volgende'}
          </button>
          {stepNum > 1 && (
            <button onClick={handleBack} className="border border-brand text-brand rounded-btn px-6 py-3 font-medium">
              Terug
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
