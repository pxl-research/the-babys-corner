import type { AccessoryItem } from '../api/client'

interface Props {
  accessory: AccessoryItem
  onClick: () => void
}

export default function CrossSellChip({ accessory, onClick }: Props) {
  return (
    <button
      onClick={onClick}
      className="text-sm text-brand-dark underline-offset-2 underline hover:text-brand-dark/80"
    >
      + {accessory.name}
    </button>
  )
}
