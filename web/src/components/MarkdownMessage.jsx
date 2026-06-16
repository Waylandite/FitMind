import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

const markdownComponents = {
  p: ({ children }) => <p className="my-2 first:mt-0 last:mb-0">{children}</p>,
  strong: ({ children }) => <strong className="font-extrabold text-[var(--text)]">{children}</strong>,
  ul: ({ children }) => <ul className="my-3 list-disc space-y-1.5 pl-5">{children}</ul>,
  ol: ({ children }) => <ol className="my-3 list-decimal space-y-1.5 pl-5">{children}</ol>,
  li: ({ children }) => <li className="pl-1 leading-7">{children}</li>,
  blockquote: ({ children }) => (
    <blockquote className="my-3 border-l-4 border-[rgba(79,140,255,0.28)] bg-[rgba(79,140,255,0.05)] px-4 py-2 text-[var(--text-soft)]">
      {children}
    </blockquote>
  ),
  code: ({ inline, children }) =>
    inline ? (
      <code className="rounded-md bg-[rgba(18,32,51,0.06)] px-1.5 py-0.5 font-mono text-[0.92em] text-[#345196]">
        {children}
      </code>
    ) : (
      <code className="block whitespace-pre-wrap break-words font-mono text-[13px] leading-6 text-[#203047]">
        {children}
      </code>
    ),
  pre: ({ children }) => (
    <pre className="app-scrollbar my-3 overflow-x-auto rounded-[1rem] bg-[#101927] px-4 py-3 shadow-inner">
      {children}
    </pre>
  ),
  a: ({ children, href }) => (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="font-semibold text-[var(--accent)] underline decoration-[rgba(79,140,255,0.32)] underline-offset-4"
    >
      {children}
    </a>
  ),
  table: ({ children }) => (
    <div className="app-scrollbar my-3 overflow-x-auto rounded-[1rem] border border-[rgba(33,52,48,0.08)]">
      <table className="min-w-full border-collapse text-sm">{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th className="border-b border-[rgba(33,52,48,0.08)] bg-[rgba(79,140,255,0.06)] px-3 py-2 text-left font-bold">
      {children}
    </th>
  ),
  td: ({ children }) => <td className="border-b border-[rgba(33,52,48,0.06)] px-3 py-2">{children}</td>,
  hr: () => <hr className="my-4 border-[rgba(33,52,48,0.08)]" />,
}

function MarkdownMessage({ content, fallback = '' }) {
  const source = content || fallback

  if (!source) {
    return null
  }

  return (
    <div className="markdown-message break-words text-[15px] leading-7 tracking-[0.005em] text-[var(--text)] sm:text-[16px]">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
        {source}
      </ReactMarkdown>
    </div>
  )
}

export default MarkdownMessage
