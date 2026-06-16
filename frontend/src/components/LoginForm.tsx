import Header from './Header'

interface Props {
  title: string
  username: string
  password: string
  onUsername: (v: string) => void
  onPassword: (v: string) => void
  onSubmit: (e: React.FormEvent) => void
  error?: boolean
}

// Shared staff/admin login screen. Credentials are sent to /api/auth/login and
// never stored client-side (the backend sets an HttpOnly cookie).
export default function LoginForm({
  title, username, password, onUsername, onPassword, onSubmit, error,
}: Props) {
  return (
    <div className="min-h-screen bg-cream text-ink font-sans">
      <Header />
      <div className="max-w-sm mx-auto px-6 py-12">
        <h1 className="font-display text-2xl font-bold mb-6">{title}</h1>
        <form onSubmit={onSubmit} className="flex flex-col gap-4">
          <input
            type="text" placeholder="Gebruikersnaam" value={username}
            onChange={(e) => onUsername(e.target.value)}
            className="border-2 border-muted rounded-card px-4 py-3 bg-white outline-none focus:border-brand"
          />
          <input
            type="password" placeholder="Wachtwoord" value={password}
            onChange={(e) => onPassword(e.target.value)}
            className="border-2 border-muted rounded-card px-4 py-3 bg-white outline-none focus:border-brand"
          />
          {error && <p className="text-danger text-sm">Ongeldige inloggegevens.</p>}
          <button type="submit" className="bg-brand text-ink rounded-btn px-6 py-3 font-medium">
            Inloggen
          </button>
        </form>
      </div>
    </div>
  )
}
