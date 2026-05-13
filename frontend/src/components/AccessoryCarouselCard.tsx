import type { AccessoryItem } from '../api/client'

interface Props {
  accessory: AccessoryItem
  onClick: () => void
}

export default function AccessoryCarouselCard({ accessory, onClick }: Props) {
  return (
    <button
      onClick={onClick}
      className="w-40 min-w-40 rounded-card border border-muted/60 bg-white p-2 text-left"
    >
      {accessory.image_url && (
        <img
          src={accessory.image_url}
          alt={accessory.name}
          className="w-full h-24 object-contain rounded-card bg-white mb-2"
        />
      )}
      <p className="text-sm text-ink leading-snug min-h-10 overflow-hidden">{accessory.name}</p>
      {!accessory.is_available && (
        <span className="bg-muted/60 text-ink/60 text-xs px-2 py-0.5 rounded-full mt-1 inline-block">
          Niet beschikbaar
        </span>
      )}
    </button>
  )
}
