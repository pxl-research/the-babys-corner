import type { StaffSession } from '../api/client'

interface Props {
  sessions: StaffSession[]
  onSelect: (code: string) => void
  emptyLabel?: string
}

// Shared recent-sessions list used by the staff and admin views.
export default function SessionList({ sessions, onSelect, emptyLabel = 'Geen sessies gevonden.' }: Props) {
  return (
    <div className="space-y-2">
      {sessions.map((s) => (
        <button
          key={s.session_id}
          onClick={() => onSelect(s.session_code)}
          className="w-full text-left bg-white rounded-card p-4 border border-muted hover:border-brand transition-colors"
        >
          <div className="flex justify-between items-start">
            <div>
              <p className="font-mono font-bold text-ink">{s.session_code}</p>
              <p className="text-sm text-ink/60">
                {s.source} · Profiel {s.profile} · {s.started_at.slice(0, 10)}
              </p>
            </div>
            <span
              className={`text-xs px-2 py-0.5 rounded-full ${
                s.status === 'handed_off' ? 'bg-brand/20 text-brand' : 'bg-muted text-ink/60'
              }`}
            >
              {s.status}
            </span>
          </div>
        </button>
      ))}
      {sessions.length === 0 && <p className="text-ink/50 text-sm">{emptyLabel}</p>}
    </div>
  )
}
