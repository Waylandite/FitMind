import { useEffect, useMemo, useRef, useState } from 'react'
import AgentThoughtProcess from '../components/AgentThoughtProcess'
import MarkdownMessage from '../components/MarkdownMessage'
import useSmartAutoScroll from '../hooks/useSmartAutoScroll'

const quickPrompts = [
  '记录今天的腿部训练和有氧',
  '补充午餐、晚餐与蛋白质摄入',
  '回顾最近 7 天的体重变化',
  '总结这周恢复情况和睡眠质量',
]

const profileHighlights = [
  { label: '身高', value: '176 cm' },
  { label: '体重', value: '71.8 kg' },
  { label: '目标', value: '减脂并保持力量' },
]

const memoryPreferences = [
  { label: '训练记忆', value: '优先记住动作、组数、RPE 和完成感受。' },
  { label: '身体状态', value: '持续追踪体重、睡眠时长、疲劳和恢复节奏。' },
  { label: '饮食习惯', value: '偏高蛋白、工作日快记录，允许后补热量估算。' },
]

const apiBaseUrl =
  import.meta.env.VITE_AGENT_BASE_URL?.replace(/\/$/, '') ?? 'http://127.0.0.1:8000/api/v1'

const emptyAssistantCard = {
  id: 'starter-assistant',
  role: 'assistant',
  content: '新的会话已经创建。现在可以直接告诉我你的训练、饮食、睡眠或身体状态。',
}

function getTimestampMs() {
  return Date.now()
}

function getPerfNow() {
  return performance.now()
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
    return { label: '你', badge: 'user' }
  }

  if (role === 'system') {
    return { label: '系统', badge: 'system' }
  }

  return { label: 'FitMind', badge: 'assistant' }
}

function workflowLabel(workflow) {
  const labels = {
    nutrition_record: '饮食记录草稿',
    body_status_record: '身体状态草稿',
    workout_record: '训练记录草稿',
    workout_plan_update: '长期训练计划草稿',
  }

  return labels[workflow] ?? '记录草稿'
}

function formatJsonForEdit(value) {
  if (!value) {
    return ''
  }

  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

function buildDraftCorrectionPrefill(event) {
  if (event.draft_actions?.correction_prefill) {
    return event.draft_actions.correction_prefill
  }

  const source = event.payload ?? event.draft ?? {}
  return `请修改这条${workflowLabel(event.workflow)}：${buildEditableDraftText(event.workflow, source)}`
}

function buildEditableDraftText(workflow, payload) {
  if (!payload) {
    return ''
  }

  if (workflow === 'nutrition_record') {
    const items = payload.nutrition?.items ?? []
    if (items.length > 0) {
      return items
        .map((item) =>
          [item.original_text || item.food_name, item.amount_g ? `${item.amount_g}g` : '']
            .filter(Boolean)
            .join(' '),
        )
        .join('；')
    }
    return payload.nutrition?.raw_text ?? payload.summary_text ?? ''
  }

  if (workflow === 'body_status_record') {
    const body = payload.body_status ?? {}
    return [
      body.raw_text,
      body.sleep_hours ? `睡眠${body.sleep_hours}小时` : '',
      body.fatigue_level ? `疲劳${body.fatigue_level}/10` : '',
      body.stress_level ? `压力${body.stress_level}/10` : '',
      body.soreness_level ? `酸痛${body.soreness_level}/10` : '',
      body.body_weight_kg ? `体重${body.body_weight_kg}kg` : '',
      body.mood ? `情绪${body.mood}` : '',
    ]
      .filter(Boolean)
      .join('，')
  }

  if (workflow === 'workout_record') {
    const exercises = payload.exercises ?? []
    if (exercises.length > 0) {
      return exercises
        .map((item) =>
          [
            item.exercise_name,
            item.sets_count ? `${item.sets_count}组` : '',
            item.reps_text,
            item.weight_text,
            item.duration_text,
          ]
            .filter(Boolean)
            .join(' '),
        )
        .join('；')
    }
    return payload.raw_text ?? payload.summary_text ?? ''
  }

  if (workflow === 'workout_plan_update') {
    return payload.raw_text ?? payload.summary_text ?? payload.title ?? ''
  }

  return ''
}

function buildDraftCardFromWorkflow(event) {
  if (!['draft_created', 'draft_updated'].includes(event.action) || !event.draft_actions) {
    return null
  }

  return {
    id: `${event.workflow}-${event.draft_id ?? Date.now()}`,
    workflow: event.workflow,
    draftId: event.draft_id,
    label: event.draft_actions.label ?? workflowLabel(event.workflow),
    hint:
      event.draft_actions.hint ??
      `请确认这条${workflowLabel(event.workflow)}：可以直接保存、取消，或点击纠正错误后修改内容再发送。`,
    confirmText: event.draft_actions.confirm_text ?? '确认保存',
    cancelText: event.draft_actions.cancel_text ?? '取消保存',
    correctionText: event.draft_actions.correction_text ?? '纠正错误',
    correctionPrefill: buildDraftCorrectionPrefill(event),
    payload: event.payload ?? event.draft ?? null,
  }
}

function buildDraftPreview(card) {
  if (!card?.payload) {
    return '草稿已生成，等待你的确认。'
  }

  const payload = card.payload
  if (card.workflow === 'nutrition_record') {
    const items = payload.nutrition?.items ?? []
    if (items.length > 0) {
      return items
        .map((item) => {
          const amount = item.amount_g ? `${item.amount_g}g` : '份量待确认'
          const calories = item.calories_kcal ? ` · ${item.calories_kcal}kcal` : ''
          return `${item.food_name ?? '食物'} ${amount}${calories}`
        })
        .join('；')
    }
    return payload.nutrition?.raw_text ?? payload.summary_text ?? '饮食草稿已生成。'
  }

  if (card.workflow === 'body_status_record') {
    const body = payload.body_status ?? {}
    const parts = [
      body.sleep_hours ? `睡眠 ${body.sleep_hours}h` : '',
      body.fatigue_level ? `疲劳 ${body.fatigue_level}/10` : '',
      body.soreness_level ? `酸痛 ${body.soreness_level}/10` : '',
      body.body_weight_kg ? `体重 ${body.body_weight_kg}kg` : '',
      body.mood ? `情绪 ${body.mood}` : '',
    ].filter(Boolean)
    return parts.join('；') || body.raw_text || payload.summary_text || '身体状态草稿已生成。'
  }

  if (card.workflow === 'workout_record') {
    const exercises = payload.exercises ?? []
    if (exercises.length > 0) {
      return exercises
        .map((item) =>
          [item.exercise_name, item.sets_count ? `${item.sets_count}组` : '', item.reps_text, item.weight_text]
            .filter(Boolean)
            .join(' · '),
        )
        .join('；')
    }
    return payload.summary_text ?? '训练草稿已生成。'
  }

  if (card.workflow === 'workout_plan_update') {
    return [payload.title, payload.raw_text].filter(Boolean).join('：') || payload.summary_text || '计划草稿已生成。'
  }

  return formatJsonForEdit(payload)
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

function buildMessageId(prefix) {
  const randomPart =
    typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(16).slice(2)}`

  return `${prefix}-${randomPart}`
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

function formatDuration(ms) {
  if (!Number.isFinite(ms) || ms < 0) {
    return '0.0s'
  }

  return `${(ms / 1000).toFixed(1)}s`
}

function isDraftGenerationTrace(event) {
  if (!event) {
    return false
  }

  if (event.workflow === 'nutrition_record') {
    return [
      'nutrition_record',
      'nutrition_react',
      'llm_decide',
      'tool_execute',
      'payload_validate',
      'draft_create',
    ].includes(event.node)
  }

  if (event.workflow === 'recent_health_summary') {
    return [
      'summary_start',
      'query_workout_records',
      'query_nutrition_records',
      'query_body_status_records',
      'query_workout_plans',
      'query_latest_workout_plan',
      'summary_llm',
    ].includes(event.node)
  }

  return false
}

function normalizeDayStart(dateLike) {
  const date = new Date(dateLike)
  date.setHours(0, 0, 0, 0)
  return date
}

function groupSessionsByDate(sessions) {
  const now = normalizeDayStart(new Date())
  const yesterday = new Date(now)
  yesterday.setDate(yesterday.getDate() - 1)
  const pastWeek = new Date(now)
  pastWeek.setDate(pastWeek.getDate() - 7)

  const groups = {
    今天: [],
    昨天: [],
    '过去 7 天': [],
    更早: [],
  }

  sessions.forEach((sessionItem, index) => {
    const basis = sessionItem.last_message_at ?? sessionItem.updated_at ?? sessionItem.created_at
    const date = basis ? normalizeDayStart(basis) : null
    const item = { ...sessionItem, _index: index }

    if (!date) {
      groups.更早.push(item)
      return
    }

    if (date.getTime() === now.getTime()) {
      groups.今天.push(item)
      return
    }

    if (date.getTime() === yesterday.getTime()) {
      groups.昨天.push(item)
      return
    }

    if (date >= pastWeek) {
      groups['过去 7 天'].push(item)
      return
    }

    groups.更早.push(item)
  })

  return Object.entries(groups).filter(([, items]) => items.length > 0)
}

async function createSessionRecordForUser(userId) {
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

function SkeletonMessage({ lines = 3 }) {
  return (
    <div className="flex gap-4 py-4">
      <div className="skeleton-shimmer h-9 w-9 shrink-0 rounded-full" />
      <div className="min-w-0 flex-1 space-y-3">
        <div className="skeleton-shimmer h-4 w-24 rounded-full" />
        {Array.from({ length: lines }).map((_, index) => (
          <div
            key={index}
            className="skeleton-shimmer h-4 rounded-full"
            style={{ width: `${index === lines - 1 ? 68 : 100}%` }}
          />
        ))}
      </div>
    </div>
  )
}

function SessionSection({
  groups,
  activeSessionId,
  handleSelectSession,
  loadingSessions,
  sending,
}) {
  if (loadingSessions) {
    return (
      <div className="space-y-4">
        <div className="skeleton-shimmer h-4 w-16 rounded-full" />
        <div className="space-y-3">
          <div className="skeleton-shimmer h-16 rounded-[1.5rem]" />
          <div className="skeleton-shimmer h-16 rounded-[1.5rem]" />
          <div className="skeleton-shimmer h-16 rounded-[1.5rem]" />
        </div>
      </div>
    )
  }

  if (!groups.length) {
    return <p className="text-sm text-[var(--text-soft)]">还没有任何会话。</p>
  }

  return groups.map(([label, items]) => (
    <section key={label}>
      <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.26em] text-[var(--text-faint)]">
        {label}
      </p>
      <div className="space-y-2">
        {items.map((sessionItem) => {
          const isActive = sessionItem.id === activeSessionId

          return (
            <button
              key={sessionItem.id}
              type="button"
              onClick={() => handleSelectSession(sessionItem.id)}
              disabled={sending}
              className={`block w-full rounded-[1.35rem] px-4 py-3 text-left transition-all duration-300 ${
                isActive
                  ? 'bg-[rgba(79,140,255,0.08)] text-[var(--text)]'
                  : 'text-[var(--text-soft)] hover:bg-[rgba(41,51,80,0.04)] hover:text-[var(--text)]'
              }`}
            >
              <p className="line-clamp-2 text-sm font-semibold leading-6">
                {formatSessionTitle(sessionItem, sessionItem._index)}
              </p>
              <p className="mt-1 text-xs text-[var(--text-faint)]">
                {sessionItem.last_message_at
                  ? `最近活跃 ${formatMessageTime(sessionItem.last_message_at)}`
                  : '尚未开始对话'}
              </p>
            </button>
          )
        })}
      </div>
    </section>
  ))
}

function DraftActionCard({ card, disabled, onAction }) {
  if (!card) {
    return null
  }

  return (
    <div className="mt-4 rounded-[1.4rem] border border-[rgba(74,91,137,0.1)] bg-[rgba(255,255,255,0.72)] p-4 shadow-[0_14px_38px_rgba(92,105,148,0.08)]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[var(--text-faint)]">
            Draft Review
          </p>
          <h3 className="mt-1 text-base font-semibold text-[var(--text)]">{card.label}</h3>
        </div>
        {card.resolvedLabel ? (
          <span className="rounded-full bg-[rgba(119,199,176,0.12)] px-3 py-1 text-xs font-semibold text-[#3f8f79]">
            {card.resolvedLabel}
          </span>
        ) : card.draftId ? (
          <span className="rounded-full bg-[rgba(79,140,255,0.08)] px-3 py-1 text-xs font-semibold text-[var(--accent)]">
            #{card.draftId}
          </span>
        ) : null}
      </div>

      <p className="mt-3 line-clamp-4 whitespace-pre-wrap text-sm leading-7 text-[var(--text-soft)]">
        {buildDraftPreview(card)}
      </p>
      <p className="mt-3 text-xs leading-6 text-[var(--text-faint)]">{card.hint}</p>

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          disabled={disabled}
          onClick={() => onAction('confirm', card)}
          className="rounded-full bg-[linear-gradient(135deg,#5f89ff,#76d0b5)] px-4 py-2 text-sm font-semibold text-white shadow-[0_12px_24px_rgba(98,134,255,0.2)] transition-all duration-300 hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-55"
        >
          {card.confirmText}
        </button>
        <button
          type="button"
          disabled={disabled}
          onClick={() => onAction('cancel', card)}
          className="rounded-full bg-[rgba(215,99,99,0.08)] px-4 py-2 text-sm font-semibold text-[var(--danger)] transition-all duration-300 hover:bg-[rgba(215,99,99,0.12)] disabled:cursor-not-allowed disabled:opacity-55"
        >
          {card.cancelText}
        </button>
        <button
          type="button"
          disabled={disabled}
          onClick={() => onAction('correct', card)}
          className="rounded-full bg-[rgba(33,52,48,0.06)] px-4 py-2 text-sm font-semibold text-[var(--text)] transition-all duration-300 hover:bg-[rgba(33,52,48,0.1)] disabled:cursor-not-allowed disabled:opacity-55"
        >
          {card.correctionText}
        </button>
      </div>
    </div>
  )
}

function HourglassLoader() {
  return (
    <span className="hourglass-flow" aria-hidden="true">
      <span className="hourglass-flow__glass">⌛</span>
      <span className="hourglass-flow__sand" />
    </span>
  )
}

function MessageRow({ message, sending, onDraftAction, now }) {
  const meta = roleMeta(message.role)
  const isUser = message.role === 'user'
  const isStreamingAssistant = message.role === 'assistant' && message.streaming
  const isWaitingFirstToken = isStreamingAssistant && !message.firstTokenAtMs && !message.content
  const thinkingMs =
    message.thinkingMs ??
    (isWaitingFirstToken && message.requestStartedAtMs ? Math.max(0, now - message.requestStartedAtMs) : null)
  const visibleAgentTrace = (message.agentTrace ?? []).filter(isDraftGenerationTrace)

  return (
    <article
      className={`flex gap-3 py-4 ${isUser ? 'justify-end' : 'justify-start'} ${
        isStreamingAssistant ? 'streaming-rise' : ''
      }`}
    >
      {!isUser ? (
        <div className="mt-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[linear-gradient(135deg,rgba(124,92,255,0.1),rgba(93,181,255,0.14),rgba(126,214,173,0.14))] text-sm font-semibold text-[#5168ff]">
          ✦
        </div>
      ) : null}

      <div
        className={`min-w-0 max-w-[min(82%,860px)] ${isUser ? 'items-end' : 'items-start'}`}
      >
        <div className={`mb-1 flex items-center gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
          <p className="text-sm font-semibold text-[var(--text)]">{meta.label}</p>
          <p className="text-xs text-[var(--text-faint)]">
            {formatMessageTime(message.createdAt) || (message.streaming ? '生成中' : '')}
          </p>
          {message.streaming ? (
            <span className="inline-flex items-center gap-1.5 text-xs text-[var(--text-faint)]">
              <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-[var(--accent)]" />
              <HourglassLoader />
              {isWaitingFirstToken ? `思考中 ${formatDuration(thinkingMs ?? 0)}` : '正在输入'}
            </span>
          ) : null}
          {!message.streaming && message.thinkingMs ? (
            <span className="rounded-full bg-[rgba(69,92,150,0.06)] px-2 py-1 text-xs text-[var(--text-faint)]">
              思考 {formatDuration(message.thinkingMs)}
            </span>
          ) : null}
        </div>

        {!isUser ? (
          <>
            <AgentThoughtProcess events={visibleAgentTrace} streaming={message.streaming} />
            <div
              className="mt-3 rounded-[1.4rem] rounded-bl-md bg-[rgba(255,255,255,0.78)] px-4 py-3 shadow-[0_14px_36px_rgba(77,92,123,0.08)] ring-1 ring-[rgba(35,52,76,0.06)] backdrop-blur-xl"
            >
              <MarkdownMessage
                content={message.content}
                fallback={isWaitingFirstToken ? 'FitMind 正在理解你的记录...' : ''}
              />
            </div>
            <DraftActionCard
              card={message.draftCard}
              disabled={sending || Boolean(message.draftCard?.resolvedLabel)}
              onAction={(action, card) => onDraftAction(action, card, message.id)}
            />
          </>
        ) : (
          <div className="whitespace-pre-wrap break-words rounded-[1.4rem] rounded-br-md bg-[linear-gradient(135deg,#5f89ff,#74ceb5)] px-4 py-3 text-[15px] leading-7 tracking-[0.005em] text-white shadow-[0_16px_34px_rgba(95,137,255,0.22)] sm:text-[16px]">
            {message.content}
          </div>
        )}
      </div>

      {isUser ? (
        <div className="mt-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[rgba(80,113,255,0.1)] text-sm font-semibold text-[var(--accent)]">
          {meta.label.slice(0, 1)}
        </div>
      ) : null}
    </article>
  )
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
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [thinkingNow, setThinkingNow] = useState(0)
  const {
    viewportRef,
    bottomAnchorRef,
    requestAutoScroll,
    resumeAutoScroll,
    handleScroll: handleSmartScroll,
    handleWheel,
    handleTouchMove,
  } = useSmartAutoScroll({ threshold: 96 })
  const composerRef = useRef(null)
  const isComposingRef = useRef(false)
  const assistantMessageIdRef = useRef(null)
  const typewriterQueueRef = useRef('')
  const typewriterTimerRef = useRef(null)
  const streamStartedAtRef = useRef(0)
  const firstTokenAtRef = useRef(null)
  const pendingFinishRef = useRef(false)
  const userId = session.userId ?? 1

  const activeSession = useMemo(
    () => sessions.find((item) => item.id === activeSessionId) ?? null,
    [sessions, activeSessionId],
  )

  const groupedSessions = useMemo(() => groupSessionsByDate(sessions), [sessions])

  const finishAssistantTyping = () => {
    const assistantId = assistantMessageIdRef.current
    if (!assistantId) {
      return
    }

    setMessages((current) =>
      current.map((message) =>
        message.id === assistantId
          ? {
              ...message,
              streaming: false,
            }
          : message,
      ),
    )
    assistantMessageIdRef.current = null
    pendingFinishRef.current = false
    setSending(false)
    requestAutoScroll('smooth')
  }

  const scheduleTypewriter = () => {
    if (typewriterTimerRef.current) {
      return
    }

    const tick = () => {
      const assistantId = assistantMessageIdRef.current
      if (!assistantId) {
        typewriterQueueRef.current = ''
        typewriterTimerRef.current = null
        pendingFinishRef.current = false
        return
      }

      const queued = typewriterQueueRef.current
      if (!queued) {
        typewriterTimerRef.current = null
        if (pendingFinishRef.current) {
          finishAssistantTyping()
        }
        return
      }

      const take = Math.min(queued.length, queued.length > 48 ? 4 : 2)
      const nextText = queued.slice(0, take)
      typewriterQueueRef.current = queued.slice(take)

      setMessages((current) =>
        current.map((message) =>
          message.id === assistantId
            ? {
                ...message,
                content: `${message.content}${nextText}`,
                streaming: true,
              }
            : message,
        ),
      )

      typewriterTimerRef.current = window.setTimeout(tick, 18)
    }

    typewriterTimerRef.current = window.setTimeout(tick, 0)
  }

  const appendAssistantDelta = (content) => {
    if (!content || !assistantMessageIdRef.current) {
      return
    }

    if (!firstTokenAtRef.current) {
      const now = getPerfNow()
      firstTokenAtRef.current = now
      const thinkingMs = streamStartedAtRef.current ? now - streamStartedAtRef.current : 0
      const assistantId = assistantMessageIdRef.current

      setMessages((current) =>
        current.map((message) =>
          message.id === assistantId
            ? {
                ...message,
                firstTokenAtMs: Date.now(),
                thinkingMs,
              }
            : message,
        ),
      )
    }

    typewriterQueueRef.current += content
    scheduleTypewriter()
  }

  const markAssistantDone = () => {
    pendingFinishRef.current = true
    scheduleTypewriter()
  }

  useEffect(() => {
    requestAutoScroll(sending ? 'auto' : 'smooth')
  }, [messages, sending, requestAutoScroll])

  useEffect(() => {
    if (!sending) {
      return undefined
    }

    const timer = window.setInterval(() => {
        setThinkingNow(getTimestampMs())
    }, 200)

    return () => {
      window.clearInterval(timer)
    }
  }, [sending])

  useEffect(
    () => () => {
      if (typewriterTimerRef.current) {
        window.clearTimeout(typewriterTimerRef.current)
      }
    },
    [],
  )

  useEffect(() => {
    if (!composerRef.current) {
      return
    }

    composerRef.current.style.height = '0px'
    const nextHeight = Math.min(composerRef.current.scrollHeight, 184)
    composerRef.current.style.height = `${Math.max(nextHeight, 28)}px`
  }, [draft])

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
          const created = await createSessionRecordForUser(userId)
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
      const created = await createSessionRecordForUser(userId)
      setSessions((current) => [created, ...current])
      resumeAutoScroll('auto')
      setActiveSessionId(created.id)
      setMessages([emptyAssistantCard])
      setConnectionState('新会话已创建')
      setSidebarOpen(false)
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

    resumeAutoScroll('auto')
    setActiveSessionId(sessionId)
    setConnectionState('已切换会话')
    setSidebarOpen(false)
  }

  const handleSend = async (prefill) => {
    const text = (prefill ?? draft).trim()

    if (!text || sending || !activeSession) {
      return
    }

    setErrorMessage('')

    const userMessage = {
      id: buildMessageId('user'),
      role: 'user',
      content: text,
      createdAt: new Date().toISOString(),
    }

    const assistantId = buildMessageId('assistant')
    assistantMessageIdRef.current = assistantId
    streamStartedAtRef.current = getPerfNow()
    firstTokenAtRef.current = null
    typewriterQueueRef.current = ''
    pendingFinishRef.current = false
    if (typewriterTimerRef.current) {
      window.clearTimeout(typewriterTimerRef.current)
      typewriterTimerRef.current = null
    }

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
          requestStartedAtMs: getTimestampMs(),
          agentTrace: [],
        },
      ]
    })

    setDraft('')
    setSending(true)
    setThinkingNow(getTimestampMs())
    setConnectionState('正在思考')
    resumeAutoScroll('auto')

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
          persist_log: true,
        }),
      })

      if (!response.ok || !response.body) {
        throw new Error(`请求失败: ${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''
      let streamFinished = false

      const handleStreamEvent = (event) => {
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

        if (event.type === 'agent_state') {
          const traceEvent = {
            ...event,
            id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
            receivedAt: new Date().toISOString(),
          }
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantMessageIdRef.current
                ? {
                    ...message,
                    agentTrace: [...(message.agentTrace ?? []), traceEvent],
                  }
                : message,
            ),
          )
          requestAutoScroll('auto')
          if (event.title) {
            setConnectionState(event.title)
          }
          return
        }

        if (event.type === 'workflow') {
          const draftCard = buildDraftCardFromWorkflow(event)
          if (draftCard) {
            setMessages((current) =>
              current.map((message) =>
                message.id === assistantMessageIdRef.current
                  ? {
                      ...message,
                      draftCard,
                    }
                : message,
              ),
            )
            requestAutoScroll('auto')
          }
          return
        }

        if (event.type === 'delta') {
          appendAssistantDelta(event.content ?? '')
          requestAutoScroll('auto')
          setConnectionState('正在输入')
          return
        }

        if (event.type === 'done') {
          streamFinished = true
          if (event.reply && !firstTokenAtRef.current) {
            appendAssistantDelta(event.reply)
          }
          markAssistantDone()
          requestAutoScroll('smooth')
          if (event.intent) {
            const percent = Math.round((event.intent_confidence ?? 0) * 100)
            setConnectionState(`已完成 · ${event.intent} · ${percent}%`)
          } else {
            setConnectionState(`已完成 · ${event.model ?? 'deepseek-v4-flash'}`)
          }
          return
        }

        if (event.type === 'error') {
          streamFinished = true
          typewriterQueueRef.current = ''
          pendingFinishRef.current = false
          if (typewriterTimerRef.current) {
            window.clearTimeout(typewriterTimerRef.current)
            typewriterTimerRef.current = null
          }
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
          assistantMessageIdRef.current = null
        }
      }

      while (true) {
        const { value, done } = await reader.read()
        if (done) {
          break
        }

        buffer += decoder.decode(value, { stream: true })
        buffer = parseSseBuffer(buffer, handleStreamEvent)
      }

      buffer += decoder.decode()
      if (buffer.trim()) {
        parseSseBuffer(`${buffer}\n\n`, handleStreamEvent)
      }

      if (!streamFinished) {
        typewriterQueueRef.current = ''
        pendingFinishRef.current = false
        if (typewriterTimerRef.current) {
          window.clearTimeout(typewriterTimerRef.current)
          typewriterTimerRef.current = null
        }
        setErrorMessage('本次对话流提前结束，后端没有返回完整结果。')
        setConnectionState('连接中断')
        setMessages((current) =>
          current.map((message) =>
            message.id === assistantMessageIdRef.current
              ? {
                  ...message,
                  content: message.content || '本次请求在业务处理过程中中断，请稍后重试。',
                  streaming: false,
                }
              : message,
          ),
        )
        assistantMessageIdRef.current = null
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
      assistantMessageIdRef.current = null
      requestAutoScroll('auto')
    } finally {
      if (!pendingFinishRef.current && !typewriterQueueRef.current) {
        assistantMessageIdRef.current = null
        setSending(false)
        requestAutoScroll('auto')
      }
    }
  }

  const handleDraftAction = (action, card, messageId) => {
    if (sending || !card) {
      return
    }

    if (action === 'confirm') {
      setMessages((current) =>
        current.map((message) =>
          message.id === messageId
            ? {
                ...message,
                draftCard: {
                  ...message.draftCard,
                  resolvedLabel: '已提交确认',
                  hint: '确认请求已发送，FitMind 正在写入记录。',
                },
              }
            : message,
        ),
      )
      handleSend(card.confirmText || '确认保存')
      return
    }

    if (action === 'cancel') {
      setMessages((current) =>
        current.map((message) =>
          message.id === messageId
            ? {
                ...message,
                draftCard: {
                  ...message.draftCard,
                  resolvedLabel: '已提交取消',
                  hint: '取消请求已发送，FitMind 正在处理草稿状态。',
                },
              }
            : message,
        ),
      )
      handleSend(card.cancelText || '取消保存')
      return
    }

    if (action === 'correct') {
      setDraft(card.correctionPrefill || '')
      setMessages((current) =>
        current.map((message) =>
          message.id === messageId
            ? {
                ...message,
                draftCard: {
                  ...message.draftCard,
                  hint: '已把当前提取结果复制到输入框，你可以修改后发送。',
                },
              }
            : message,
        ),
      )
      requestAnimationFrame(() => {
        composerRef.current?.focus()
      })
    }
  }

  const handleComposerKeyDown = (event) => {
    const nativeEvent = event.nativeEvent
    const isImeConfirming =
      nativeEvent.isComposing || isComposingRef.current || nativeEvent.keyCode === 229

    if (isImeConfirming) {
      return
    }

    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      handleSend()
    }
  }

  const closeOverlays = () => {
    setSidebarOpen(false)
    setSettingsOpen(false)
    setProfileOpen(false)
  }

  return (
    <main className="relative h-screen overflow-hidden bg-[#fbfbfd] text-[var(--text)]">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(126,150,255,0.08),transparent_28%),radial-gradient(circle_at_85%_20%,rgba(133,208,181,0.07),transparent_26%),linear-gradient(180deg,#fcfcfe_0%,#fbfbfd_100%)]" />

      <button
        type="button"
        onClick={() => setSidebarOpen(true)}
        className="fixed left-4 top-4 z-40 inline-flex h-11 w-11 items-center justify-center rounded-full text-[var(--text-soft)] transition-all duration-300 hover:bg-[rgba(46,56,87,0.06)] hover:text-[var(--text)]"
        aria-label="打开历史记录"
      >
        <span className="flex flex-col gap-1.5">
          <span className="block h-0.5 w-4 rounded-full bg-current" />
          <span className="block h-0.5 w-4 rounded-full bg-current" />
          <span className="block h-0.5 w-4 rounded-full bg-current" />
        </span>
      </button>

      <div className="fixed right-4 top-4 z-40 sm:right-6 sm:top-5">
        <div className="relative">
          <button
            type="button"
            onClick={() => setProfileOpen((current) => !current)}
            className="inline-flex h-11 w-11 items-center justify-center rounded-full bg-[rgba(255,255,255,0.84)] text-sm font-semibold text-[var(--text)] shadow-[0_10px_30px_rgba(86,101,145,0.12)] backdrop-blur-xl transition-all duration-300 hover:-translate-y-0.5"
          >
            {session.name?.slice(0, 1) ?? 'F'}
          </button>

          <div
            className={`absolute right-0 top-[calc(100%+0.8rem)] w-72 rounded-[1.6rem] bg-[rgba(255,255,255,0.92)] p-3 shadow-[0_20px_55px_rgba(88,99,137,0.16)] backdrop-blur-2xl transition-all duration-300 ${
              profileOpen
                ? 'pointer-events-auto translate-y-0 opacity-100'
                : 'pointer-events-none -translate-y-2 opacity-0'
            }`}
          >
            <div className="rounded-[1.25rem] bg-[linear-gradient(135deg,rgba(105,132,255,0.07),rgba(116,212,174,0.07))] px-4 py-4">
              <p className="text-sm font-semibold text-[var(--text)]">{session.name}</p>
              <p className="mt-1 text-xs text-[var(--text-faint)]">{session.identifier}</p>
            </div>

            <div className="mt-3 space-y-1">
              <button
                type="button"
                onClick={() => {
                  setSettingsOpen(true)
                  setProfileOpen(false)
                }}
                className="block w-full rounded-[1rem] px-3 py-3 text-left text-sm font-medium text-[var(--text)] transition-all duration-300 hover:bg-[rgba(52,74,140,0.05)]"
              >
                用户记忆设置
              </button>
              <button
                type="button"
                onClick={onLogout}
                className="block w-full rounded-[1rem] px-3 py-3 text-left text-sm font-medium text-[var(--danger)] transition-all duration-300 hover:bg-[rgba(215,99,99,0.06)]"
              >
                退出账号
              </button>
            </div>
          </div>
        </div>
      </div>

      <div
        className={`fixed inset-0 z-30 bg-[rgba(28,34,51,0.14)] backdrop-blur-[2px] transition-all duration-300 ${
          sidebarOpen || settingsOpen || profileOpen
            ? 'pointer-events-auto opacity-100'
            : 'pointer-events-none opacity-0'
        }`}
        onClick={closeOverlays}
      />

      <aside
        className={`fixed inset-y-0 left-0 z-40 w-[22rem] max-w-[calc(100vw-1.5rem)] transform bg-[rgba(255,255,255,0.86)] px-4 py-4 shadow-[0_22px_70px_rgba(74,87,129,0.12)] backdrop-blur-2xl transition-all duration-300 ease-in-out ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-[110%]'
        }`}
      >
        <div className="flex h-full flex-col overflow-hidden rounded-[1.9rem] bg-[rgba(255,255,255,0.56)] px-3 py-3">
          <div className="flex items-start justify-between gap-4 px-3 py-3">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-[var(--text-faint)]">
                History
              </p>
              <h2 className="mt-2 font-display text-[2rem] leading-none tracking-[-0.045em] text-[var(--text)]">
                健身记录
              </h2>
            </div>
            <button
              type="button"
              onClick={() => setSidebarOpen(false)}
              className="inline-flex h-10 w-10 items-center justify-center rounded-full text-[var(--text-faint)] transition-all duration-300 hover:bg-[rgba(46,56,87,0.06)] hover:text-[var(--text)]"
              aria-label="关闭历史记录"
            >
              ×
            </button>
          </div>

          <button
            type="button"
            onClick={handleCreateSession}
            disabled={creatingSession || sending}
            className="mx-3 mt-1 rounded-full bg-[linear-gradient(135deg,#648bff,#79d0b5)] px-4 py-3 text-sm font-semibold text-white shadow-[0_12px_26px_rgba(100,139,255,0.24)] transition-all duration-300 hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {creatingSession ? '创建中...' : '新建对话'}
          </button>

          <div className="app-scrollbar mt-5 flex-1 space-y-5 overflow-y-auto px-3 pb-3">
            <SessionSection
              groups={groupedSessions}
              activeSessionId={activeSessionId}
              handleSelectSession={handleSelectSession}
              loadingSessions={loadingSessions}
              sending={sending}
            />
          </div>
        </div>
      </aside>

      <aside
        className={`fixed inset-y-0 right-0 z-40 w-full max-w-sm transform bg-[rgba(255,255,255,0.88)] px-4 py-4 shadow-[-14px_0_50px_rgba(82,98,141,0.08)] backdrop-blur-2xl transition-all duration-300 ease-in-out ${
          settingsOpen ? 'translate-x-0' : 'translate-x-[110%]'
        }`}
      >
        <div className="flex h-full flex-col rounded-[1.9rem] bg-[rgba(255,255,255,0.58)] px-5 py-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-[var(--text-faint)]">
                Memory
              </p>
              <h3 className="mt-2 font-display text-[2rem] leading-none tracking-[-0.045em] text-[var(--text)]">
                用户记忆
              </h3>
              <p className="mt-3 text-sm leading-6 text-[var(--text-soft)]">
                让助手更准确地理解你的身体数据和长期目标。
              </p>
            </div>
            <button
              type="button"
              onClick={() => setSettingsOpen(false)}
              className="inline-flex h-10 w-10 items-center justify-center rounded-full text-[var(--text-faint)] transition-all duration-300 hover:bg-[rgba(46,56,87,0.06)] hover:text-[var(--text)]"
              aria-label="关闭设置"
            >
              ×
            </button>
          </div>

          <div className="mt-6 grid gap-3 sm:grid-cols-3">
            {profileHighlights.map((item) => (
              <div key={item.label} className="rounded-[1.2rem] bg-[rgba(85,104,170,0.04)] px-4 py-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[var(--text-faint)]">
                  {item.label}
                </p>
                <p className="mt-2 text-sm font-semibold text-[var(--text)]">{item.value}</p>
              </div>
            ))}
          </div>

          <div className="app-scrollbar mt-6 flex-1 space-y-3 overflow-y-auto pr-1">
            {memoryPreferences.map((item) => (
              <article key={item.label} className="rounded-[1.35rem] bg-[rgba(255,255,255,0.74)] px-4 py-4 shadow-[0_8px_24px_rgba(96,110,150,0.06)]">
                <p className="text-sm font-semibold text-[var(--text)]">{item.label}</p>
                <p className="mt-2 text-sm leading-7 text-[var(--text-soft)]">{item.value}</p>
              </article>
            ))}
          </div>
        </div>
      </aside>

      <section className="relative mx-auto flex h-screen min-h-0 w-[min(96vw,1560px)] flex-col overflow-hidden px-4 pb-32 pt-14 sm:px-6 sm:pt-16 lg:px-8">
        <header className="mx-auto flex w-full max-w-[1120px] items-start justify-between gap-4">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-[var(--text-faint)]">
              FitMind Console
            </p>
            <h1 className="mt-1.5 max-w-[760px] truncate font-display text-[1.55rem] leading-tight tracking-[-0.04em] text-[var(--text)] sm:text-[1.95rem]">
              {activeSession ? formatSessionTitle(activeSession, 0) : '准备你的下一次记录'}
            </h1>
          </div>
          <div className="hidden items-center gap-2 text-sm text-[var(--text-faint)] sm:flex">
            <span className={`pulse-dot h-2 w-2 rounded-full ${sending ? 'bg-[var(--accent)]' : 'bg-[var(--mint)]'}`} />
            <span>{connectionState}</span>
          </div>
        </header>

        <div
          ref={viewportRef}
          onScroll={handleSmartScroll}
          onWheel={handleWheel}
          onTouchMove={handleTouchMove}
          className="app-scrollbar relative mt-5 min-h-0 flex-1 overflow-y-auto overscroll-contain"
        >
          <div className="mx-auto w-full max-w-[1120px] pb-36">
            <div className="mb-4 flex flex-wrap gap-2">
              {quickPrompts.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => handleSend(prompt)}
                  className="rounded-full bg-[rgba(90,108,180,0.05)] px-3.5 py-1.5 text-xs font-medium text-[var(--text-soft)] transition-all duration-300 hover:bg-[rgba(90,108,180,0.09)] hover:text-[var(--text)]"
                >
                  {prompt}
                </button>
              ))}
            </div>

            {loadingMessages ? (
              <div className="space-y-3">
                <SkeletonMessage lines={4} />
                <SkeletonMessage lines={3} />
                <SkeletonMessage lines={5} />
              </div>
            ) : (
              <div className="space-y-1">
                {messages.map((message) => (
                  <MessageRow
                    key={message.id}
                    message={message}
                    sending={sending}
                    now={thinkingNow}
                    onDraftAction={handleDraftAction}
                  />
                ))}
              </div>
            )}
            <div ref={bottomAnchorRef} className="h-1" aria-hidden="true" />
          </div>
        </div>

        <div className="pointer-events-none fixed bottom-5 left-1/2 z-30 w-[min(1120px,calc(100%-1.5rem))] -translate-x-1/2 sm:w-[min(1120px,calc(100%-3rem))]">
          <div className="mx-auto max-w-[1040px]">
            {errorMessage ? (
              <div className="pointer-events-auto mb-3 rounded-[1.4rem] bg-[rgba(255,255,255,0.86)] px-4 py-3 text-sm text-[var(--danger)] shadow-[0_14px_35px_rgba(215,99,99,0.08)] backdrop-blur-xl">
                {errorMessage}
              </div>
            ) : null}

            <div className="pointer-events-auto rounded-[2rem] bg-[rgba(255,255,255,0.84)] px-4 py-3 shadow-[0_18px_50px_rgba(78,89,121,0.12)] backdrop-blur-2xl sm:px-5">
              <div className="flex items-end gap-3">
                <textarea
                  ref={composerRef}
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  onCompositionStart={() => {
                    isComposingRef.current = true
                  }}
                  onCompositionEnd={() => {
                    isComposingRef.current = false
                  }}
                  onKeyDown={handleComposerKeyDown}
                  placeholder="记录今天的训练、饮食、睡眠或体重变化..."
                  rows={1}
                  className="max-h-[184px] min-h-[28px] flex-1 resize-none overflow-y-auto bg-transparent px-1 py-2 text-[15px] leading-7 text-[var(--text)] outline-none placeholder:text-[var(--text-faint)]"
                />

                <div className="mb-1 flex shrink-0 items-center gap-1">
                  <button
                    type="button"
                    className="inline-flex h-10 w-10 items-center justify-center rounded-full text-[var(--text-faint)] transition-all duration-300 hover:bg-[rgba(46,56,87,0.06)] hover:text-[var(--text)]"
                    aria-label="语音输入"
                  >
                    话
                  </button>
                  <button
                    type="button"
                    className="inline-flex h-10 w-10 items-center justify-center rounded-full text-[var(--text-faint)] transition-all duration-300 hover:bg-[rgba(46,56,87,0.06)] hover:text-[var(--text)]"
                    aria-label="上传图片"
                  >
                    图
                  </button>
                  <button
                    type="button"
                    onClick={() => handleSend()}
                    disabled={sending || !draft.trim() || !activeSession}
                    className={`inline-flex h-11 w-11 items-center justify-center rounded-full text-sm font-semibold transition-all duration-300 ${
                      sending || !draft.trim() || !activeSession
                        ? 'bg-[rgba(96,110,150,0.08)] text-[var(--text-faint)]'
                        : 'bg-[linear-gradient(135deg,#5f89ff,#76d0b5)] text-white shadow-[0_14px_30px_rgba(98,134,255,0.24)] hover:-translate-y-0.5'
                    }`}
                    aria-label="发送消息"
                  >
                    ↑
                  </button>
                </div>
              </div>

              <div className="mt-2 flex items-center justify-between gap-4 px-1">
                <p className="text-xs text-[var(--text-faint)]">Enter 发送，Shift + Enter 换行</p>
                <p className="hidden text-xs text-[var(--text-faint)] sm:block">
                  当前会话会自动继承最近历史上下文
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  )
}

export default ChatWorkspace
