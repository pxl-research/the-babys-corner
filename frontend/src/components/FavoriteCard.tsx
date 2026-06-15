import type { NamedItem } from '../api/client'

// Read-only product card for staff-facing favorites: mirrors the customer
// overview card (image + brand + name) but without the favorite/CTA controls.
export default function FavoriteCard({ item }: { item: NamedItem }) {
  return (
    <div className="rounded-card overflow-hidden bg-white border border-muted/50 flex flex-col">
      {item.image_url && (
        <img
          src={item.image_url}
          alt={item.name}
          className="w-full h-32 object-contain bg-white"
        />
      )}
      <div className="p-3">
        <p className="text-[10px] font-semibold tracking-widest uppercase text-ink/70 mb-0.5">
          {item.brand}
        </p>
        <h4 className="text-sm font-medium text-ink leading-snug">{item.name}</h4>
        {item.price != null && (
          <p className="text-sm text-ink/80 mt-1">€ {item.price.toFixed(2)}</p>
        )}
      </div>
    </div>
  )
}
