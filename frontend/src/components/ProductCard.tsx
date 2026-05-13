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
          <p className="text-xs font-semibold tracking-widest uppercase text-ink/60 mb-0.5">{stroller.brand}</p>
          <h3 className="font-medium text-ink leading-snug mb-1 min-h-14">{stroller.name}</h3>
          <p className="font-medium text-ink">€ {stroller.price.toFixed(2)}</p>
          {!stroller.is_available && (
            <span className="bg-muted/60 text-ink/60 text-xs px-2 py-0.5 rounded-full mt-1 inline-block">
              Niet beschikbaar
            </span>
          )}
        </div>
      </button>
      <div className="px-4 pb-4 flex items-center justify-between mt-auto">
        <div />
        <button
          onClick={onToggleFavorite}
          disabled={locked}
          className="text-2xl disabled:opacity-40 ml-2"
        >
          {isFavorited ? '♥' : '♡'}
        </button>
      </div>
    </div>
  )
}
