import { Fragment } from 'react'

// Minimal, dependency-free Markdown renderer for product copy: headings (#..####),
// bullet lists (- / *), bold (**...**) and paragraphs. Builds React nodes directly,
// so there is no HTML injection. Plain (non-Markdown) text renders as paragraphs.

function renderInline(text: string) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith('**') && part.endsWith('**') ? (
      <strong key={i}>{part.slice(2, -2)}</strong>
    ) : (
      <Fragment key={i}>{part}</Fragment>
    )
  )
}

export default function Markdown({ text, className }: { text: string; className?: string }) {
  const lines = text.replace(/\r\n/g, '\n').split('\n')
  const blocks: JSX.Element[] = []
  let list: string[] = []
  let key = 0

  const flushList = () => {
    if (!list.length) return
    const items = list
    blocks.push(
      <ul key={key++} className="list-disc pl-5 space-y-1 mb-3">
        {items.map((it, i) => (
          <li key={i}>{renderInline(it)}</li>
        ))}
      </ul>
    )
    list = []
  }

  for (const raw of lines) {
    const line = raw.trim()
    if (!line) {
      flushList()
      continue
    }
    const heading = /^#{1,4}\s+(.*)$/.exec(line)
    if (heading) {
      flushList()
      blocks.push(
        <p key={key++} className="font-semibold text-ink mt-3 mb-1">
          {renderInline(heading[1])}
        </p>
      )
      continue
    }
    const bullet = /^[-*]\s+(.*)$/.exec(line)
    if (bullet) {
      list.push(bullet[1])
      continue
    }
    flushList()
    blocks.push(
      <p key={key++} className="mb-3">
        {renderInline(line)}
      </p>
    )
  }
  flushList()

  return <div className={className}>{blocks}</div>
}
