import { useNavigate, useParams } from 'react-router-dom'
import { useEffect, useState } from 'react'
import Header from '../components/Header'
import ProgressDots from '../components/ProgressDots'
import { api } from '../api/client'
import type { CollectionSelection } from '../api/client'
import { useSessionStore } from '../store/sessionStore'

const TOTAL_STEPS = 9

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
    availableTags, setAvailableTags,
    filterTagsSelected, setFilterTagsSelected,
    availableBrands, setAvailableBrands,
    filterBrandsSelected, setFilterBrandsSelected,
    availableCollections, setAvailableCollections,
    filterCollectionsSelected, setFilterCollectionsSelected,
  } = useSessionStore()

  const [submitting, setSubmitting] = useState(false)
  const filledDots = quizAnswers.filter((a) => a !== undefined).length

  useEffect(() => {
    if (!quizConfig) {
      api.getQuizConfig().then(setQuizConfig).catch(console.error)
    }
  }, [quizConfig, setQuizConfig])

  // Load tags on step 5 (prefetch) or step 6 (direct navigation / refresh)
  useEffect(() => {
    if ((stepNum === 5 || stepNum === 6) && availableTags.length === 0) {
      api.getTags().then((r) => setAvailableTags(r.tags)).catch(console.error)
    }
  }, [stepNum, availableTags.length, setAvailableTags])

  // ── Steps 1–5: profile questions ────────────────────────────────────────────

  function handleOptionSelect(index: number) {
    setAnswer(stepNum, index)
  }

  async function handleNext() {
    if (stepNum < 5) {
      navigate(`/quiz/${stepNum + 1}`)
      return
    }
    // Step 5 → submit quiz, then go to tags filter
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
    navigate('/quiz/6')
  }

  function handleBack() {
    if (stepNum === 1) navigate('/')
    else navigate(`/quiz/${stepNum - 1}`)
  }

  // ── Step 6: tags filter ──────────────────────────────────────────────────────

  function toggleTag(tag: string) {
    setFilterTagsSelected(
      filterTagsSelected.includes(tag)
        ? filterTagsSelected.filter((t) => t !== tag)
        : [...filterTagsSelected, tag]
    )
  }

  async function handleTagsNext() {
    setSubmitting(true)
    try {
      const result = await api.filterTags(filterTagsSelected)
      setAvailableBrands(result.brands)
      navigate('/quiz/7')
    } finally {
      setSubmitting(false)
    }
  }

  // ── Step 7: brands filter ────────────────────────────────────────────────────

  function toggleBrand(brand: string) {
    setFilterBrandsSelected(
      filterBrandsSelected.includes(brand)
        ? filterBrandsSelected.filter((b) => b !== brand)
        : [...filterBrandsSelected, brand]
    )
  }

  async function handleBrandsNext() {
    setSubmitting(true)
    try {
      const result = await api.filterBrands(filterBrandsSelected)
      setAvailableCollections(result.brands)
      navigate('/quiz/8')
    } finally {
      setSubmitting(false)
    }
  }

  // ── Step 8: collections filter ───────────────────────────────────────────────

  function collectionKey(sel: CollectionSelection) {
    return `${sel.brand}::${sel.collection ?? ''}`
  }

  function toggleCollection(sel: CollectionSelection) {
    const key = collectionKey(sel)
    const exists = filterCollectionsSelected.some((s) => collectionKey(s) === key)
    setFilterCollectionsSelected(
      exists
        ? filterCollectionsSelected.filter((s) => collectionKey(s) !== key)
        : [...filterCollectionsSelected, sel]
    )
  }

  async function handleCollectionsNext() {
    setSubmitting(true)
    try {
      await api.filterCollections(filterCollectionsSelected)
      navigate('/quiz/9')
    } finally {
      setSubmitting(false)
    }
  }

  // ── Step 9: optional note ────────────────────────────────────────────────────

  async function handleNoteSubmit(note: string) {
    if (submitting) return
    setSubmitting(true)
    try {
      await api.saveNote(note)
      navigate('/recommendations')
    } finally {
      setSubmitting(false)
    }
  }

  // ── Loading guard ────────────────────────────────────────────────────────────

  if (!quizConfig) {
    return (
      <div className="min-h-screen bg-cream flex items-center justify-center">
        <p className="text-ink/50">Laden…</p>
      </div>
    )
  }

  // ── Render ───────────────────────────────────────────────────────────────────

  const question = quizConfig.questions[stepNum - 1]
  const selectedOption = quizAnswers[stepNum - 1] ?? -1

  // Step 9: optional note
  if (stepNum === 9) {
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
          <p className="text-sm text-ink/60 text-center max-w-xs">
            We vergelijken jullie wensen met ons volledige assortiment. Dit duurt even.
          </p>
        </div>
      )
    }

    return (
      <div className="min-h-screen bg-cream text-ink font-sans">
        <Header />
        <div className="max-w-lg mx-auto px-6 py-8">
          <ProgressDots total={TOTAL_STEPS} current={9} filled={filledDots} />
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
              onClick={() => handleNoteSubmit(optionalNote)}
              className="bg-brand text-white rounded-btn px-6 py-3 font-medium"
            >
              {noteConfig.continue_label}
            </button>
            <button onClick={() => navigate('/quiz/8')} className="border border-brand text-brand rounded-btn px-6 py-3 font-medium">
              Terug
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Step 8: collections filter
  if (stepNum === 8) {
    const collectionOptions: CollectionSelection[] = availableCollections.flatMap((bc) =>
      bc.collections.length > 0
        ? bc.collections.map<CollectionSelection>((c) => ({ brand: bc.brand, collection: c }))
        : [{ brand: bc.brand, collection: null } as CollectionSelection]
    )

    return (
      <div className="min-h-screen bg-cream text-ink font-sans">
        <Header />
        <div className="max-w-lg mx-auto px-6 py-8">
          <ProgressDots total={TOTAL_STEPS} current={8} filled={filledDots} />
          <p className="font-display text-xl font-bold text-ink mt-6 mb-2">Welke collecties spreken jullie aan?</p>
          <p className="text-sm text-ink/60 mb-6">Laat leeg voor alle collecties van de geselecteerde merken.</p>
          <div className="flex flex-col gap-2">
            {collectionOptions.map((opt) => {
              const key = collectionKey(opt)
              const selected = filterCollectionsSelected.some((s) => collectionKey(s) === key)
              const label = opt.collection
                ? `${capitalize(opt.brand)} – ${opt.collection}`
                : capitalize(opt.brand)
              return (
                <button
                  key={key}
                  onClick={() => toggleCollection(opt)}
                  className={[
                    'border-2 rounded-card p-4 w-full text-left transition-colors',
                    selected ? 'border-brand bg-brand/10' : 'border-muted hover:border-brand/50',
                  ].join(' ')}
                >
                  {label}
                </button>
              )
            })}
          </div>
          <div className="flex flex-col gap-3 mt-8">
            <button
              onClick={handleCollectionsNext}
              disabled={submitting}
              className="bg-brand text-white rounded-btn px-6 py-3 font-medium disabled:opacity-50"
            >
              {submitting ? 'Bezig…' : 'Volgende'}
            </button>
            <button onClick={() => navigate('/quiz/7')} className="border border-brand text-brand rounded-btn px-6 py-3 font-medium">
              Terug
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Step 7: brands filter
  if (stepNum === 7) {
    return (
      <div className="min-h-screen bg-cream text-ink font-sans">
        <Header />
        <div className="max-w-lg mx-auto px-6 py-8">
          <ProgressDots total={TOTAL_STEPS} current={7} filled={filledDots} />
          <p className="font-display text-xl font-bold text-ink mt-6 mb-2">Zijn er merken die jullie aanspreken?</p>
          <p className="text-sm text-ink/60 mb-6">Meerdere keuzes mogelijk. Laat leeg voor alle merken.</p>
          <div className="flex flex-col gap-2">
            {availableBrands.map((brand) => {
              const selected = filterBrandsSelected.includes(brand)
              return (
                <button
                  key={brand}
                  onClick={() => toggleBrand(brand)}
                  className={[
                    'border-2 rounded-card p-4 w-full text-left transition-colors',
                    selected ? 'border-brand bg-brand/10' : 'border-muted hover:border-brand/50',
                  ].join(' ')}
                >
                  {capitalize(brand)}
                </button>
              )
            })}
          </div>
          <div className="flex flex-col gap-3 mt-8">
            <button
              onClick={handleBrandsNext}
              disabled={submitting}
              className="bg-brand text-white rounded-btn px-6 py-3 font-medium disabled:opacity-50"
            >
              {submitting ? 'Bezig…' : 'Volgende'}
            </button>
            <button onClick={() => navigate('/quiz/6')} className="border border-brand text-brand rounded-btn px-6 py-3 font-medium">
              Terug
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Step 6: tags filter
  if (stepNum === 6) {
    return (
      <div className="min-h-screen bg-cream text-ink font-sans">
        <Header />
        <div className="max-w-lg mx-auto px-6 py-8">
          <ProgressDots total={TOTAL_STEPS} current={6} filled={filledDots} />
          <p className="font-display text-xl font-bold text-ink mt-6 mb-2">Wat zijn jullie wensen?</p>
          <p className="text-sm text-ink/60 mb-6">Meerdere keuzes mogelijk. Laat leeg om alles te zien.</p>
          {availableTags.length === 0 ? (
            <p className="text-ink/50">Laden…</p>
          ) : (
            <div className="flex flex-col gap-2">
              {availableTags.map((tag) => {
                const selected = filterTagsSelected.includes(tag)
                return (
                  <button
                    key={tag}
                    onClick={() => toggleTag(tag)}
                    className={[
                      'border-2 rounded-card p-4 w-full text-left transition-colors',
                      selected ? 'border-brand bg-brand/10' : 'border-muted hover:border-brand/50',
                    ].join(' ')}
                  >
                    {tag}
                  </button>
                )
              })}
            </div>
          )}
          <div className="flex flex-col gap-3 mt-8">
            <button
              onClick={handleTagsNext}
              disabled={submitting || availableTags.length === 0}
              className="bg-brand text-white rounded-btn px-6 py-3 font-medium disabled:opacity-50"
            >
              {submitting ? 'Bezig…' : 'Volgende'}
            </button>
            <button onClick={() => navigate('/quiz/5')} className="border border-brand text-brand rounded-btn px-6 py-3 font-medium">
              Terug
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Steps 1–5: profile questions
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
            onClick={handleNext}
            disabled={selectedOption === -1 || submitting}
            className="bg-brand text-white rounded-btn px-6 py-3 font-medium disabled:opacity-50"
          >
            {submitting ? 'Bezig…' : stepNum === 5 ? 'Bevestig' : 'Volgende'}
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

function capitalize(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1)
}
