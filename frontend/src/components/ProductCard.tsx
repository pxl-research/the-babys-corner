import type { StrollerItem } from '../api/client'

interface Props {
  stroller: StrollerItem
  isFavorited: boolean
  onToggleFavorite: () => void
  onClick: () => void
  locked?: boolean
}

export default function ProductCard({
  stroller, isFavorited, onToggleFavorite, onClick, locked,
}: Props) {
  return (
    <div className="rounded-card shadow-sm overflow-hidden bg-white border border-muted/50 h-full flex flex-col">
      <button onClick={onClick} className="w-full text-left">
        {stroller.image_url && (
          <img src={stroller.image_url} alt={stroller.name} className="w-full h-48 object-contain bg-white" />
        )}
        <div className="p-4 min-h-44">
          <p className="text-xs font-semibold tracking-widest uppercase text-ink/70 mb-0.5">{stroller.brand}</p>
          <h3 className="font-medium text-ink leading-snug mb-1 min-h-14">{stroller.name}</h3>
          <p className="font-medium text-ink">€ {stroller.price.toFixed(2)}</p>
        </div>
      </button>
      <div className="px-4 pb-4 flex items-center justify-end mt-auto">
        <button
          onClick={onToggleFavorite}
          disabled={locked}
          aria-label={isFavorited ? 'Verwijder uit favorieten' : 'Voeg toe aan favorieten'}
          className="flex items-center gap-1 text-sm text-ink/70 disabled:opacity-40"
        >
          <span className="text-2xl leading-none">{isFavorited ? '♥' : '♡'}</span>
          <span>{isFavorited ? 'Bewaard' : 'Bewaar'}</span>
        </button>
      </div>
    </div>
  )
}
