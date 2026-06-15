interface StaffAnswer {
  question_text?: string
  option_text?: string
}

interface Props {
  answers: StaffAnswer[]
}

export default function StaffAnswerList({ answers }: Props) {
  return (
    <ol className="space-y-2">
      {answers.map((answer, index) => (
        <li
          key={`${answer.question_text ?? 'question'}-${index}`}
          className="flex gap-3 rounded-card border border-muted/70 bg-white px-3 py-3 shadow-sm"
        >
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand/15 text-sm font-semibold text-brand-dark">
            {index + 1}
          </span>
          <div className="min-w-0">
            <p className="text-xs font-medium leading-snug text-ink/70">
              {answer.question_text}
            </p>
            <p className="mt-1 text-sm font-semibold leading-snug text-ink">
              {answer.option_text}
            </p>
          </div>
        </li>
      ))}
    </ol>
  )
}
