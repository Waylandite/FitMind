import { useEffect, useMemo, useRef, useState } from 'react'

const quickPrompts = [
  '记录今天的训练计划',
  '补一条饮食记录',
  '总结今天的状态',
  '回顾最近三天训练',
]

const apiBaseUrl =
  import.meta.env.VITE_AGENT_BASE_URL?.replace(/\/$/, '') ?? 'http://127.0.0.1:8000/api/v1'

const defaultSystemPrompt =
  '你是 FitMind，一个专业、简洁、友好的健身与健康助手。请围绕用户输入，给出清晰结论和下一步建议。'

const emptyAssistantCard = {
  id: 'starter-assistant',
  role: 'assistant',
  content: '新的会话已经创建。现在可以直接告诉我你的训练、饮食或身体状态。',
}

function parseSseBuffer(buffer, onEvent) {
  const segments = buffer.split('\n\n')
  const rest = segments.pop() ?? ''

  for (const segment of segments) {
    const lines = segment
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)

    const dataLines = lines
      .filter((line) => line.startsWith('data:'))
      .map((line) => line.slice(5).trim())

    if (!dataLines.length) {
      continue
    }

    try {
      onEvent(JSON.parse(dataLines.join('\n')))
    } catch (error) {
      console.error('Failed to parse SSE payload', error)
    }
  }

  return rest
}

function roleMeta(role) {
  if (role === 'user') {
    return { label: '我', badge: 'user' }
  }

  if (role === 'system') {
    return { label: '系统', badge: 'system' }
  }

  return { label: 'AI', badge: 'assistant' }
}

function formatSessionTitle(sessionItem, index) {
  if (sessionItem.title?.trim()) {
    return sessionItem.title.trim()
  }

  return `会话 ${index + 1}`
}

function buildThreadId(userId) {
  const randomPart =
    typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(16).slice(2)}`

  return `session-${userId}-${randomPart}`
}

function formatMessageTime(value) {
  if (!value) {
    return ''
  }

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return ''
  }

  return new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

function ChatWorkspace({ session, onLogout }) {
  const [messages, setMessages] = useState([])
  const [sessions, setSessions] = useState([])
  const [activeSessionId, setActiveSessionId] = useState(null)
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const [loadingSessions, setLoadingSessions] = useState(true)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const [creatingSession, setCreatingSession] = useState(false)
  const [connectionState, setConnectionState] = useState('已连接')
  const [errorMessage, setErrorMessage] = useState('')
  const viewportRef = useRef(null)
  const assistantMessageIdRef = useRef(null)
  const userId = session.userId ?? 1

  const activeSession = useMemo(
    () => sessions.find((item) => item.id === activeSessionId) ?? null,
    [sessions, activeSessionId],
  )

  useEffect(() => {
    if (!viewportRef.current) {
      return
    }

    viewportRef.current.scrollTo({
      top: viewportRef.current.scrollHeight,
      behavior: 'smooth',
    })
  }, [messages, sending])

  useEffect(() => {
    let cancelled = false

    const bootstrap = async () => {
      setLoadingSessions(true)
      try {
        const response = await fetch(`${apiBaseUrl}/memories/sessions?user_id=${userId}`)
        if (!response.ok) {
          throw new Error(`会话列表请求失败: ${response.status}`)
        }

        const records = await response.json()
        if (cancelled) {
          return
        }

        setSessions(records)

        if (records.length > 0) {
          setActiveSessionId(records[0].id)
        } else {
          const created = await createSessionRecord()
          if (!cancelled && created) {
            setSessions([created])
            setActiveSessionId(created.id)
          }
        }
      } catch (error) {
        if (!cancelled) {
          setErrorMessage(error instanceof Error ? error.message : '加载会话失败')
        }
      } finally {
        if (!cancelled) {
          setLoadingSessions(false)
        }
      }
    }

    bootstrap()

    return () => {
      cancelled = true
    }
  }, [userId])

  useEffect(() => {
    if (!activeSessionId) {
      return
    }

    let cancelled = false

    const fetchMessages = async () => {
      setLoadingMessages(true)
      setErrorMessage('')
      try {
        const response = await fetch(`${apiBaseUrl}/memories/sessions/${activeSessionId}/messages`)
        if (!response.ok) {
          throw new Error(`会话历史请求失败: ${response.status}`)
        }

        const records = await response.json()
        if (cancelled) {
          return
        }

        if (!records.length) {
          setMessages([emptyAssistantCard])
        } else {
          setMessages(
            records.map((record) => ({
              id: `message-${record.id}`,
              role: record.role,
              content: record.message_text,
              createdAt: record.created_at,
            })),
          )
        }
      } catch (error) {
        if (!cancelled) {
          setErrorMessage(error instanceof Error ? error.message : '加载消息失败')
        }
      } finally {
        if (!cancelled) {
          setLoadingMessages(false)
        }
      }
    }

    fetchMessages()

    return () => {
      cancelled = true
    }
  }, [activeSessionId])

  const createSessionRecord = async () => {
    const response = await fetch(`${apiBaseUrl}/memories/sessions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id: userId,
        thread_id: buildThreadId(userId),
        title: '新的会话',
        status: 'active',
      }),
    })

    if (!response.ok) {
      throw new Error(`创建会话失败: ${response.status}`)
    }

    return response.json()
  }

  const refreshSessions = async (nextActiveId = activeSessionId) => {
    const response = await fetch(`${apiBaseUrl}/memories/sessions?user_id=${userId}`)
    if (!response.ok) {
      throw new Error(`刷新会话失败: ${response.status}`)
    }

    const records = await response.json()
    setSessions(records)
    if (nextActiveId) {
      setActiveSessionId(nextActiveId)
    } else if (records[0]) {
      setActiveSessionId(records[0].id)
    }
  }

  const handleCreateSession = async () => {
    if (creatingSession || sending) {
      return
    }

    setCreatingSession(true)
    setErrorMessage('')

    try {
      const created = await createSessionRecord()
      setSessions((current) => [created, ...current])
      setActiveSessionId(created.id)
      setMessages([emptyAssistantCard])
      setConnectionState('新会话已创建')
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : '创建会话失败')
    } finally {
      setCreatingSession(false)
    }
  }

  const handleSelectSession = (sessionId) => {
    if (sending || sessionId === activeSessionId) {
      return
    }

    setActiveSessionId(sessionId)
    setConnectionState('已切换会话')
  }

  const handleSend = async (prefill) => {
    const text = (prefill ?? draft).trim()

    if (!text || sending || !activeSession) {
      return
    }

    setErrorMessage('')

    const userMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text,
      createdAt: new Date().toISOString(),
    }

    const assistantId = `assistant-${Date.now()}`
    assistantMessageIdRef.current = assistantId

    setMessages((current) => {
      const cleaned =
        current.length === 1 && current[0].id === emptyAssistantCard.id ? [] : current

      return [
        ...cleaned,
        userMessage,
        {
          id: assistantId,
          role: 'assistant',
          content: '',
          streaming: true,
          createdAt: new Date().toISOString(),
        },
      ]
    })

    setDraft('')
    setSending(true)
    setConnectionState('模型正在回复')

    try {
      const response = await fetch(`${apiBaseUrl}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          thread_id: activeSession.thread_id,
          message: text,
          system_prompt: defaultSystemPrompt,
          persist_log: true,
        }),
      })

      if (!response.ok || !response.body) {
        throw new Error(`请求失败: ${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''

      while (true) {
        const { value, done } = await reader.read()
        if (done) {
          break
        }

        buffer += decoder.decode(value, { stream: true })
        buffer = parseSseBuffer(buffer, (event) => {
          if (!assistantMessageIdRef.current) {
            return
          }

          if (event.type === 'intent') {
            const percent = Math.round((event.confidence ?? 0) * 100)
            setConnectionState(`意图 ${event.intent ?? 'unknown'} · ${percent}%`)
            return
          }

          if (event.type === 'session') {
            setConnectionState(`会话 ${event.session_id} 已连接`)
            return
          }

          if (event.type === 'delta') {
            setMessages((current) =>
              current.map((message) =>
                message.id === assistantMessageIdRef.current
                  ? {
                      ...message,
                      content: `${message.content}${event.content ?? ''}`,
                      streaming: true,
                    }
                  : message,
              ),
            )
            return
          }

          if (event.type === 'done') {
            setMessages((current) =>
              current.map((message) =>
                message.id === assistantMessageIdRef.current
                  ? {
                      ...message,
                      content: event.reply ?? message.content,
                      streaming: false,
                    }
                  : message,
              ),
            )
            if (event.intent) {
              const percent = Math.round((event.intent_confidence ?? 0) * 100)
              setConnectionState(`已完成 · ${event.intent} · ${percent}%`)
            } else {
              setConnectionState(`已完成 · ${event.model ?? 'deepseek-v4-flash'}`)
            }
            return
          }

          if (event.type === 'error') {
            setErrorMessage(event.message ?? '模型流返回错误')
            setConnectionState('连接异常')
            setMessages((current) =>
              current.map((message) =>
                message.id === assistantMessageIdRef.current
                  ? {
                      ...message,
                      content: message.content || '本次请求未成功完成，请稍后重试。',
                      streaming: false,
                    }
                  : message,
              ),
            )
          }
        })
      }

      await refreshSessions(activeSession.id)
    } catch (error) {
      const message = error instanceof Error ? error.message : '请求失败'
      setErrorMessage(message)
      setConnectionState('连接异常')
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantMessageIdRef.current
            ? {
                ...message,
                content: '后端连接失败，请确认 Agent 服务已启动。',
                streaming: false,
              }
            : message,
        ),
      )
    } finally {
      assistantMessageIdRef.current = null
      setSending(false)
    }
  }

  const handleComposerKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      handleSend()
    }
  }

  return (
    <main className="min-h-screen bg-[#0b1020] text-slate-100">
      <div className="mx-auto flex h-screen max-w-[1600px] flex-col xl:flex-row">
        <aside className="flex h-[18rem] shrink-0 flex-col border-b border-slate-800 bg-slate-950 xl:h-screen xl:w-[320px] xl:border-b-0 xl:border-r">
          <div className="border-b border-slate-800 px-5 py-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-medium uppercase tracking-[0.24em] text-slate-400">
                  FitMind
                </p>
                <h1 className="mt-2 text-xl font-semibold text-white">会话管理</h1>
              </div>
              <button
                type="button"
                onClick={handleCreateSession}
                disabled={creatingSession || sending}
                className="inline-flex h-10 items-center rounded-xl bg-slate-100 px-4 text-sm font-medium text-slate-950 transition hover:bg-white disabled:cursor-not-allowed disabled:bg-slate-300"
              >
                {creatingSession ? '创建中' : '新会话'}
              </button>
            </div>
            <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-900 px-4 py-3">
              <p className="text-xs uppercase tracking-[0.24em] text-slate-500">当前用户</p>
              <p className="mt-2 text-base font-medium text-white">{session.name}</p>
              <p className="mt-1 text-sm text-slate-400">{session.identifier}</p>
            </div>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4 app-scrollbar">
            <div className="space-y-3">
              {loadingSessions ? (
                <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-6 text-sm text-slate-400">
                  正在加载会话...
                </div>
              ) : sessions.length ? (
                sessions.map((sessionItem, index) => {
                  const isActive = sessionItem.id === activeSessionId
                  return (
                    <button
                      key={sessionItem.id}
                      type="button"
                      onClick={() => handleSelectSession(sessionItem.id)}
                      className={`block w-full rounded-2xl border px-4 py-4 text-left transition ${
                        isActive
                          ? 'border-slate-500 bg-slate-800 shadow-[0_0_0_1px_rgba(255,255,255,0.04)]'
                          : 'border-slate-800 bg-slate-900 hover:border-slate-700 hover:bg-slate-800'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <p className="line-clamp-2 text-sm font-medium leading-6 text-white">
                          {formatSessionTitle(sessionItem, index)}
                        </p>
                        <span className="shrink-0 rounded-full bg-slate-800 px-2 py-1 text-[11px] text-slate-400">
                          #{index + 1}
                        </span>
                      </div>
                      <p className="mt-3 text-xs text-slate-400">
                        {sessionItem.last_message_at
                          ? `最近活跃 ${formatMessageTime(sessionItem.last_message_at)}`
                          : '尚未开始对话'}
                      </p>
                    </button>
                  )
                })
              ) : (
                <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-6 text-sm text-slate-400">
                  还没有任何会话。
                </div>
              )}
            </div>
          </div>

          <div className="border-t border-slate-800 px-4 py-4">
            <button
              type="button"
              onClick={onLogout}
              className="inline-flex h-11 w-full items-center justify-center rounded-xl border border-slate-700 bg-slate-900 text-sm font-medium text-slate-200 transition hover:border-slate-600 hover:bg-slate-800"
            >
              退出登录
            </button>
          </div>
        </aside>

        <section className="flex min-h-0 flex-1 flex-col">
          <header className="shrink-0 border-b border-slate-800 bg-slate-950/85 px-5 py-4 backdrop-blur">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0">
                <h2 className="truncate text-lg font-semibold text-white">
                  {activeSession ? formatSessionTitle(activeSession, 0) : '正在准备会话'}
                </h2>
                <p className="mt-1 text-sm text-slate-400">
                  {activeSession
                    ? '消息会持续写入当前会话，并自动带上最近历史。'
                    : '请选择一个会话开始对话。'}
                </p>
              </div>
              <div className="inline-flex items-center gap-2 self-start rounded-full border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-300">
                <span className={`h-2.5 w-2.5 rounded-full ${sending ? 'bg-emerald-400' : 'bg-slate-500'}`} />
                <span>{connectionState}</span>
              </div>
            </div>
          </header>

          <div className="min-h-0 flex-1 overflow-y-auto bg-slate-950/40 px-4 py-5 sm:px-6 app-scrollbar">
            <div
              ref={viewportRef}
              className="mx-auto flex min-h-full w-full max-w-4xl flex-col gap-4"
            >
              {loadingMessages ? (
                <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-6 text-sm text-slate-400">
                  正在加载当前会话...
                </div>
              ) : (
                messages.map((message) => {
                  const meta = roleMeta(message.role)
                  const isUser = message.role === 'user'
                  const isSystem = message.role === 'system'

                  return (
                    <article
                      key={message.id}
                      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`w-full max-w-3xl rounded-3xl border px-4 py-4 shadow-sm sm:px-5 ${
                          isUser
                            ? 'border-emerald-500/30 bg-emerald-500/10'
                            : isSystem
                              ? 'border-amber-400/25 bg-amber-400/10'
                              : 'border-slate-800 bg-slate-900'
                        }`}
                      >
                        <div className="mb-3 flex items-center justify-between gap-3">
                          <div className="flex items-center gap-3">
                            <span
                              className={`inline-flex h-9 w-9 items-center justify-center rounded-full text-sm font-semibold ${
                                meta.badge === 'user'
                                  ? 'bg-emerald-500/20 text-emerald-200'
                                  : meta.badge === 'system'
                                    ? 'bg-amber-400/20 text-amber-100'
                                    : 'bg-slate-800 text-slate-100'
                              }`}
                            >
                              {meta.label}
                            </span>
                            <div>
                              <p className="text-sm font-medium text-white">{meta.label}</p>
                              <p className="text-xs text-slate-400">
                                {formatMessageTime(message.createdAt) || (message.streaming ? '生成中' : '')}
                              </p>
                            </div>
                          </div>
                          {message.streaming ? (
                            <span className="rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-300">
                              输出中
                            </span>
                          ) : null}
                        </div>
                        <div className="whitespace-pre-wrap break-words text-[15px] leading-7 text-slate-100">
                          {message.content}
                        </div>
                      </div>
                    </article>
                  )
                })
              )}
            </div>
          </div>

          <footer className="shrink-0 border-t border-slate-800 bg-slate-950 px-4 py-4 sm:px-6">
            <div className="mx-auto flex w-full max-w-4xl flex-col gap-4">
              {errorMessage ? (
                <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">
                  {errorMessage}
                </div>
              ) : null}

              <div className="flex flex-wrap gap-2">
                {quickPrompts.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => handleSend(prompt)}
                    className="rounded-full border border-slate-700 bg-slate-900 px-4 py-2 text-sm text-slate-200 transition hover:border-slate-600 hover:bg-slate-800"
                  >
                    {prompt}
                  </button>
                ))}
              </div>

              <div className="rounded-3xl border border-slate-800 bg-slate-900 p-3 shadow-sm">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
                  <textarea
                    value={draft}
                    onChange={(event) => setDraft(event.target.value)}
                    onKeyDown={handleComposerKeyDown}
                    placeholder="输入今天的训练、饮食或身体状态。按 Enter 发送，Shift + Enter 换行。"
                    rows={3}
                    className="min-h-[104px] flex-1 resize-none rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm leading-6 text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-slate-500"
                  />
                  <button
                    type="button"
                    onClick={() => handleSend()}
                    disabled={sending || !draft.trim() || !activeSession}
                    className="inline-flex h-12 shrink-0 items-center justify-center rounded-2xl bg-slate-100 px-5 text-sm font-medium text-slate-950 transition hover:bg-white disabled:cursor-not-allowed disabled:bg-slate-300 sm:w-[120px]"
                  >
                    {sending ? '发送中...' : '发送'}
                  </button>
                </div>
                <p className="mt-3 text-xs leading-5 text-slate-500">
                  当前消息会写入选中的 session，并自动带上该会话最近的历史上下文。
                </p>
              </div>
            </div>
          </footer>
        </section>
      </div>
    </main>
  )
}

export default ChatWorkspace
