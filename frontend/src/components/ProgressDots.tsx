interface Props {
  total: number
  current: number
  filled: number
}

export default function ProgressDots({ total, current, filled }: Props) {
  return (
    <div className="flex gap-2 justify-center py-2">
      {Array.from({ length: total }, (_, i) => {
        const step = i + 1
        const isFilled = step <= filled
        const isActive = step === current
        return (
          <div
            key={i}
            className={[
              'w-2.5 h-2.5 rounded-full transition-all',
              isFilled ? 'bg-brand' : 'bg-muted',
              isActive ? 'ring-2 ring-brand ring-offset-1' : '',
            ].join(' ')}
          />
        )
      })}
    </div>
  )
}
