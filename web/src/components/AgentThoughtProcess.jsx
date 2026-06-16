import { useEffect, useMemo, useRef, useState } from 'react'

const statusMeta = {
  queue: {
    label: '排队',
    tone: 'bg-slate-500',
    text: 'text-slate-600',
    ring: 'ring-slate-200',
  },
  thinking: {
    label: '分析中',
    tone: 'bg-blue-500',
    text: 'text-blue-700',
    ring: 'ring-blue-100',
  },
  tool_call: {
    label: '调用工具',
    tone: 'bg-amber-500',
    text: 'text-amber-700',
    ring: 'ring-amber-100',
  },
  tool_output: {
    label: '工具返回',
    tone: 'bg-emerald-500',
    text: 'text-emerald-700',
    ring: 'ring-emerald-100',
  },
  success: {
    label: '完成',
    tone: 'bg-teal-500',
    text: 'text-teal-700',
    ring: 'ring-teal-100',
  },
  error: {
    label: '异常',
    tone: 'bg-rose-500',
    text: 'text-rose-700',
    ring: 'ring-rose-100',
  },
}

function formatDuration(ms) {
  if (!Number.isFinite(ms) || ms < 0) {
    return '0.0s'
  }

  return `${(ms / 1000).toFixed(1)}s`
}

function compactJson(value) {
  if (!value) {
    return ''
  }

  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

function AgentThoughtProcess({ events = [], streaming = false, onAutoScroll }) {
  const [expanded, setExpanded] = useState(false)
  const scrollRef = useRef(null)

  const latestEvent = events[events.length - 1]
  const completedCount = useMemo(
    () => events.filter((event) => ['success', 'tool_output'].includes(event.status)).length,
    [events],
  )

  useEffect(() => {
    if (!scrollRef.current) {
      onAutoScroll?.()
      return
    }

    if (!expanded) {
      onAutoScroll?.()
      return
    }

    const frameId = window.requestAnimationFrame(() => {
      scrollRef.current?.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: 'smooth',
      })
      onAutoScroll?.()
    })

    return () => {
      window.cancelAnimationFrame(frameId)
    }
  }, [events, expanded, onAutoScroll])

  if (!events.length) {
    return null
  }

  return (
    <section className="agent-thought mt-4 overflow-hidden rounded-[1.35rem] border border-[rgba(36,54,78,0.08)] bg-[linear-gradient(145deg,rgba(255,255,255,0.82),rgba(245,250,248,0.72))] shadow-[0_18px_45px_rgba(66,88,112,0.08)]">
      <button
        type="button"
        onClick={() => setExpanded((current) => !current)}
        className="flex w-full items-center justify-between gap-4 px-4 py-3 text-left transition-colors duration-300 hover:bg-white/60"
      >
        <span className="flex min-w-0 items-center gap-3">
          <span className="relative flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#122033] text-[11px] font-bold tracking-[0.18em] text-white shadow-[0_10px_22px_rgba(18,32,51,0.2)]">
            AI
            {streaming ? <span className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full bg-[#70e0b4] shadow-[0_0_0_5px_rgba(112,224,180,0.16)]" /> : null}
          </span>
          <span className="min-w-0">
            <span className="block text-sm font-semibold text-[var(--text)]">
              {expanded ? '隐藏思考过程' : '查看思考过程'}
            </span>
            <span className="block truncate text-xs text-[var(--text-faint)]">
              {latestEvent?.title ?? 'Agent 正在编排执行链路'}
            </span>
          </span>
        </span>

        <span className="flex shrink-0 items-center gap-2">
          <span className="rounded-full bg-[rgba(18,32,51,0.06)] px-2.5 py-1 text-xs text-[var(--text-soft)]">
            {completedCount}/{events.length}
          </span>
          <span className={`text-sm text-[var(--text-faint)] transition-transform duration-300 ${expanded ? 'rotate-180' : ''}`}>
            ⌄
          </span>
        </span>
      </button>

      <div
        className={`grid transition-[grid-template-rows] duration-500 ease-[cubic-bezier(0.22,1,0.36,1)] ${
          expanded ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'
        }`}
      >
        <div className="min-h-0 overflow-hidden">
          <div ref={scrollRef} className="app-scrollbar max-h-[260px] overflow-y-auto px-4 pb-4">
            <ol className="relative ml-3 space-y-3 border-l border-[rgba(39,57,84,0.11)] pl-5">
              {events.map((event, index) => {
                const meta = statusMeta[event.status] ?? statusMeta.thinking
                return (
                  <li
                    key={event.id ?? `${event.node}-${index}`}
                    className="agent-thought-step relative rounded-[1rem] bg-white/68 px-3.5 py-3 shadow-[0_10px_26px_rgba(70,85,105,0.06)] ring-1 ring-black/[0.03]"
                    style={{ animationDelay: `${Math.min(index * 28, 180)}ms` }}
                  >
                    <span className={`absolute -left-[1.86rem] top-4 h-3 w-3 rounded-full ${meta.tone} ring-4 ${meta.ring}`} />
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`rounded-full bg-white px-2 py-0.5 text-[11px] font-semibold ${meta.text} ring-1 ${meta.ring}`}>
                        {meta.label}
                      </span>
                      <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-[var(--text-faint)]">
                        {event.workflow ?? 'agent'} / {event.node ?? 'node'}
                      </span>
                      {event.elapsed_ms !== undefined ? (
                        <span className="ml-auto font-mono text-[11px] text-[var(--text-faint)]">
                          +{formatDuration(event.elapsed_ms)}
                        </span>
                      ) : null}
                    </div>

                    <p className="mt-2 text-sm font-semibold text-[var(--text)]">{event.title ?? '执行状态更新'}</p>
                    {event.detail ? (
                      <p className="mt-1 text-xs leading-5 text-[var(--text-soft)]">{event.detail}</p>
                    ) : null}

                    {event.tool_name ? (
                      <div className="mt-2 rounded-xl bg-[rgba(18,32,51,0.04)] px-3 py-2 font-mono text-[11px] text-[var(--text-soft)]">
                        <div>tool: {event.tool_name}</div>
                        {event.arguments ? <pre className="mt-1 whitespace-pre-wrap break-words">{compactJson(event.arguments)}</pre> : null}
                      </div>
                    ) : null}

                    {event.output ? (
                      <details className="mt-2 rounded-xl bg-[rgba(112,224,180,0.08)] px-3 py-2 text-xs text-[var(--text-soft)]">
                        <summary className="cursor-pointer font-semibold text-emerald-700">查看工具返回</summary>
                        <pre className="mt-2 whitespace-pre-wrap break-words font-mono text-[11px] leading-5">{compactJson(event.output)}</pre>
                      </details>
                    ) : null}
                  </li>
                )
              })}
            </ol>
          </div>
        </div>
      </div>
    </section>
  )
}

export default AgentThoughtProcess
