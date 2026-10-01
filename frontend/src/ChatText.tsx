import { Fragment } from 'react'

// A deliberately small formatting vocabulary: text, emphasis, paragraphs and lists.
// React escapes every string. HTML, URLs and unsupported Markdown remain inert text.
function inline(text: string) {
  return text.split(/(\*\*[^*\n]+\*\*)/g).map((part, index) =>
    part.startsWith('**') && part.endsWith('**') && part.length > 4
      ? <strong key={index}>{part.slice(2, -2)}</strong> : part)
}

export function ChatText({ text }: { text: string }) {
  const lines = text.replace(/\r\n/g, '\n').split('\n')
  const blocks = []
  let index = 0
  while (index < lines.length) {
    if (!lines[index].trim()) { index++; continue }
    const list = lines[index].match(/^\s*(?:(\d{1,3})[.)]|[-*])\s+(.+)$/)
    if (list) {
      const ordered = !!list[1]
      const start = Number(list[1] || 1)
      const items = []
      while (index < lines.length) {
        const item = lines[index].match(/^\s*(?:(\d{1,3})[.)]|[-*])\s+(.+)$/)
        if (!item || !!item[1] !== ordered) break
        items.push(<li key={index}>{inline(item[2])}</li>); index++
      }
      blocks.push(ordered ? <ol key={index} start={start}>{items}</ol> : <ul key={index}>{items}</ul>)
    } else {
      const paragraph = []
      while (index < lines.length && lines[index].trim() && !/^\s*(?:\d{1,3}[.)]|[-*])\s+.+$/.test(lines[index])) {
        paragraph.push(<Fragment key={index}>{paragraph.length > 0 && <br />}{inline(lines[index])}</Fragment>); index++
      }
      blocks.push(<p key={index}>{paragraph}</p>)
    }
  }
  return <div className="chat-text">{blocks}</div>
}
