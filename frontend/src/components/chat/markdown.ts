export interface MarkdownBlock {
  type: 'paragraph' | 'list' | 'code'
  text: string
  items: string[]
  language?: string
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

  for (const line of lines) {
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
