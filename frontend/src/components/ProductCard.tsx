import type { StrollerItem, AccessoryItem } from '../api/client'
import CrossSellChip from './CrossSellChip'

interface Props {
  stroller: StrollerItem
  isFavorited: boolean
  onToggleFavorite: () => void
  onClick: () => void
  onAccessoryClick: (acc: AccessoryItem) => void
  locked?: boolean
}

export default function ProductCard({
  stroller, isFavorited, onToggleFavorite, onClick, onAccessoryClick, locked,
}: Props) {
  return (
    <div className="rounded-card shadow-sm overflow-hidden bg-white border border-muted/50">
      <button onClick={onClick} className="w-full text-left">
        {stroller.image_url && (
          <img src={stroller.image_url} alt={stroller.name} className="w-full h-48 object-contain bg-white" />
        )}
        <div className="p-4">
          <p className="text-xs font-semibold tracking-widest uppercase text-ink/60 mb-0.5">{stroller.brand}</p>
          <h3 className="font-medium text-ink leading-snug mb-1">{stroller.name}</h3>
          <p className="font-medium text-ink">€ {stroller.price.toFixed(2)}</p>
          {!stroller.is_available && (
            <span className="bg-muted/60 text-ink/60 text-xs px-2 py-0.5 rounded-full mt-1 inline-block">
              Niet beschikbaar
            </span>
          )}
        </div>
      </button>
      <div className="px-4 pb-4 flex items-center justify-between">
        <div className="flex flex-wrap gap-1">
          {stroller.show_cross_sell_chips && stroller.cross_sell_items.map((acc) => (
            <CrossSellChip key={acc.id} accessory={acc} onClick={() => onAccessoryClick(acc)} />
          ))}
        </div>
        <button
          onClick={onToggleFavorite}
          disabled={!stroller.is_available && !isFavorited || locked}
          title={!stroller.is_available ? 'Deze kinderwagen is momenteel niet beschikbaar.' : undefined}
          className="text-2xl disabled:opacity-40 ml-2"
        >
          {isFavorited ? '♥' : '♡'}
        </button>
      </div>
    </div>
  )
}
