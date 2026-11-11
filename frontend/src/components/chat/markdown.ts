export interface MarkdownBlock {
  type: 'paragraph' | 'list' | 'code' | 'table'
  text: string
  items: string[]
  language?: string
  headers?: string[]
  rows?: string[][]
}

function parseTableCells(line: string) {
  return line.trim().replace(/^\||\|$/g, '').split('|').map(cell => cell.trim())
}

function isTableSeparator(line: string) {
  const cells = line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|')

  return cells.length >= 2 && cells.every(cell => /^\s*:?-{3,}:?\s*$/.test(cell))
}

export function parseSafeMarkdown(source: string): MarkdownBlock[] {
  const lines = source.replaceAll('\r\n', '\n').split('\n')
  const blocks: MarkdownBlock[] = []
  let paragraph: string[] = []
  let list: string[] = []
  let code: string[] | null = null
  let language = ''

  const flushParagraph = () => {
    if (paragraph.length) {
      blocks.push({ type: 'paragraph', text: paragraph.join('\n'), items: [] })
      paragraph = []
    }
  }

  const flushList = () => {
    if (list.length) {
      blocks.push({ type: 'list', text: '', items: list })
      list = []
    }
  }

  for (let index = 0; index < lines.length; index++) {
    const line = lines[index] ?? ''

    if (code) {
      if (line.startsWith('```')) {
        blocks.push({ type: 'code', text: code.join('\n'), items: [], language })
        code = null
        language = ''
      }
      else {
        code.push(line)
      }

      continue
    }

    const fence = line.match(/^```(\w*)$/)

    if (fence) {
      flushParagraph()
      flushList()
      code = []
      language = fence[1] ?? ''

      continue
    }

    if (line.includes('|') && isTableSeparator(lines[index + 1] ?? '')) {
      flushParagraph()
      flushList()

      const headers = parseTableCells(line)
      const rows: string[][] = []

      index += 2

      while (index < lines.length && lines[index]?.includes('|') && lines[index]?.trim()) {
        rows.push(parseTableCells(lines[index] ?? ''))
        index++
      }

      blocks.push({ type: 'table', text: '', items: [], headers, rows })
      index--

      continue
    }

    const listItem = line.match(/^\s*[-*] (.*)$/)

    if (listItem) {
      flushParagraph()
      list.push(listItem[1] ?? '')

      continue
    }

    if (!line.trim()) {
      flushParagraph()
      flushList()

      continue
    }

    if (list.length)
      flushList()

    paragraph.push(line)
  }

  if (code)
    blocks.push({ type: 'code', text: code.join('\n'), items: [], language })

  flushParagraph()
  flushList()

  return blocks
}
