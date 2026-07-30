import { useEffect, useMemo, useRef, useState } from 'react'
import { CalendarDays, CircleUserRound, EyeOff, Mars, Ruler, Venus, Weight } from 'lucide-react'
import { DayPicker } from 'react-day-picker'
import AgentThoughtProcess from '../components/AgentThoughtProcess'
import MarkdownMessage from '../components/MarkdownMessage'
import useSmartAutoScroll from '../hooks/useSmartAutoScroll'

const quickPrompts = [
  '记录今天的腿部训练和有氧',
  '补充午餐、晚餐与蛋白质摄入',
  '回顾最近 7 天的体重变化',
  '总结这周恢复情况和睡眠质量',
]

const apiBaseUrl =
  import.meta.env.VITE_AGENT_BASE_URL?.replace(/\/$/, '') ?? 'http://127.0.0.1:8000/api/v1'

const weekdayOptions = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const genderOptions = [
  { value: '男', label: '男', Icon: Mars },
  { value: '女', label: '女', Icon: Venus },
  { value: '其他', label: '其他', Icon: CircleUserRound },
  { value: '不透露', label: '不透露', Icon: EyeOff },
]
const goalTypeOptions = ['减脂', '增肌', '维持', '塑形', '提升体能']
const trainingLevelOptions = ['新手', '初级', '中级', '高级']
const responseStyleOptions = ['简洁', '详细', '鼓励型', '直接型']
const dietStructureOptions = ['高蛋白', '低碳水', '控糖', '均衡饮食', '素食']

const memoryCategoryDefinitions = [
  {
    id: 'fitness_preference',
    title: '健身偏好',
    description: '记录你的训练目标、喜欢与不喜欢练的内容。',
    fields: [
      { key: 'goal_type', label: '训练目标', type: 'select', options: goalTypeOptions },
      { key: 'preferred_exercises', label: '偏好训练部位或动作', type: 'textarea', rows: 3 },
      { key: 'disliked_exercises', label: '不喜欢或想减少的训练', type: 'textarea', rows: 3 },
    ],
  },
  {
    id: 'content_preference',
    title: '内容偏好',
    description: '让助手知道你希望重点聊什么，或者避免哪些内容。',
    fields: [
      { key: 'focus_topics', label: '希望重点关注的话题', type: 'textarea', rows: 3 },
      { key: 'avoid_topics', label: '希望减少或避免的话题', type: 'textarea', rows: 3 },
    ],
  },
  {
    id: 'conversation_preference',
    title: '对话风格',
    description: '设定 FitMind 回答你的语气和信息密度。',
    fields: [{ key: 'response_style', label: '回答风格', type: 'radio', options: responseStyleOptions }],
  },
  {
    id: 'diet_preference',
    title: '饮食偏好',
    description: '记录你的饮食结构、忌口和不耐受情况。',
    fields: [
      { key: 'diet_structure', label: '饮食结构', type: 'select', options: dietStructureOptions },
      { key: 'avoid_foods', label: '忌口或少吃的食物', type: 'textarea', rows: 3 },
      { key: 'intolerances', label: '不耐受或过敏提示', type: 'textarea', rows: 3 },
    ],
  },
  {
    id: 'health_constraint_preference',
    title: '健康限制',
    description: '让助手在训练建议里避开风险动作和敏感点。',
    fields: [
      { key: 'injury_notes', label: '伤病说明', type: 'textarea', rows: 3 },
      { key: 'movement_restrictions', label: '动作限制', type: 'textarea', rows: 3 },
    ],
  },
]

function createEmptyProfileForm() {
  return {
    gender: '',
    birth_date: '',
    height_cm: '',
    weight_kg: '',
    target_weight_kg: '',
    goal_type: '',
    training_level: '',
    injury_notes: '',
    medical_notes: '',
    diet_preference: '',
    preferred_training_days: [],
    remark: '',
  }
}

function createEmptyMemoryForm() {
  return memoryCategoryDefinitions.reduce((accumulator, category) => {
    category.fields.forEach((field) => {
      accumulator[`${category.id}::${field.key}`] = ''
    })
    return accumulator
  }, {})
}

function mapProfileToForm(profile) {
  if (!profile) {
    return createEmptyProfileForm()
  }

  return {
    gender: profile.gender ?? '',
    birth_date: profile.birth_date ?? '',
    height_cm: profile.height_cm == null ? '' : String(profile.height_cm),
    weight_kg: profile.weight_kg == null ? '' : String(profile.weight_kg),
    target_weight_kg: profile.target_weight_kg == null ? '' : String(profile.target_weight_kg),
    goal_type: profile.goal_type ?? '',
    training_level: profile.training_level ?? '',
    injury_notes: profile.injury_notes ?? '',
    medical_notes: profile.medical_notes ?? '',
    diet_preference: profile.diet_preference ?? '',
    preferred_training_days: profile.preferred_training_days
      ? profile.preferred_training_days
          .split(',')
          .map((item) => item.trim())
          .filter(Boolean)
      : [],
    remark: profile.remark ?? '',
  }
}

function toNullableText(value) {
  const text = String(value ?? '').trim()
  return text ? text : null
}

function toNullableNumber(value) {
  if (value === '' || value == null) {
    return null
  }

  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function serializeProfileForm(form) {
  return {
    gender: toNullableText(form.gender),
    birth_date: toNullableText(form.birth_date),
    height_cm: toNullableNumber(form.height_cm),
    weight_kg: toNullableNumber(form.weight_kg),
    target_weight_kg: toNullableNumber(form.target_weight_kg),
    goal_type: toNullableText(form.goal_type),
    training_level: toNullableText(form.training_level),
    injury_notes: toNullableText(form.injury_notes),
    medical_notes: toNullableText(form.medical_notes),
    diet_preference: toNullableText(form.diet_preference),
    preferred_training_days: form.preferred_training_days.length ? form.preferred_training_days.join(',') : null,
    remark: toNullableText(form.remark),
  }
}

function getProfileSummaryItems(form) {
  const items = [
    {
      label: '身高',
      value: form.height_cm ? form.height_cm : '未填写',
      unit: form.height_cm ? 'cm' : '',
      Icon: Ruler,
      tone: 'blue',
    },
    {
      label: '体重',
      value: form.weight_kg ? form.weight_kg : '未填写',
      unit: form.weight_kg ? 'kg' : '',
      Icon: Weight,
      tone: 'mint',
    },
  ]

  return items
}

function parseDateInput(value) {
  if (!value) {
    return undefined
  }

  const date = new Date(`${value}T00:00:00`)
  return Number.isNaN(date.getTime()) ? undefined : date
}

function formatDateInput(date) {
  if (!date) {
    return ''
  }

  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function formatDisplayDate(value) {
  const date = parseDateInput(value)
  if (!date) {
    return '选择出生日期'
  }

  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  }).format(date)
}

function mapMemoriesToForm(records) {
  const nextForm = createEmptyMemoryForm()
  records.forEach((record) => {
    const fieldId = `${record.memory_category}::${record.memory_key}`
    if (Object.hasOwn(nextForm, fieldId)) {
      nextForm[fieldId] = record.memory_value ?? ''
    }
  })
  return nextForm
}

function buildMemoryRecordMap(records) {
  return records.reduce((accumulator, record) => {
    accumulator[`${record.memory_category}::${record.memory_key}`] = record
    return accumulator
  }, {})
}

function normalizeFormValue(value) {
  return String(value ?? '').trim()
}

function buildMemoryRawText(fieldLabel, value) {
  const normalized = normalizeFormValue(value)
  return normalized ? `${fieldLabel}：${normalized}` : null
}

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

  if (event.workflow === 'today_workout_recommendation' || event.workflow === 'workout_recommendation_agent') {
    return [
      'recommendation_start',
      'query_latest_workout_plan',
      'query_recent_workout_records',
      'recommendation_llm',
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

function WeekdaySelector({ value, onToggle }) {
  return (
    <div className="flex flex-wrap gap-2">
      {weekdayOptions.map((day) => {
        const selected = value.includes(day)

        return (
          <button
            key={day}
            type="button"
            onClick={() => onToggle(day)}
            className={`rounded-full px-3 py-2 text-sm font-medium transition-all duration-300 ${
              selected
                ? 'bg-[rgba(79,140,255,0.12)] text-[var(--accent)]'
                : 'bg-[rgba(56,75,121,0.05)] text-[var(--text-soft)] hover:bg-[rgba(56,75,121,0.09)] hover:text-[var(--text)]'
            }`}
          >
            {day}
          </button>
        )
      })}
    </div>
  )
}

function ProfileMetricCard({ item }) {
  const { Icon } = item
  const toneClass =
    item.tone === 'mint'
      ? 'bg-[rgba(119,199,176,0.12)] text-[#3f8f79]'
      : 'bg-[rgba(79,140,255,0.1)] text-[var(--accent)]'

  return (
    <div className="rounded-[1.15rem] border border-[rgba(62,82,130,0.06)] bg-[rgba(255,255,255,0.78)] px-4 py-4 shadow-[0_10px_28px_rgba(96,110,150,0.06)]">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[var(--text-faint)]">
            {item.label}
          </p>
          <div className="mt-2 flex items-baseline gap-1.5">
            <p className="text-2xl font-bold leading-none text-[var(--text)]">{item.value}</p>
            {item.unit ? <p className="text-sm font-semibold text-[var(--text-faint)]">{item.unit}</p> : null}
          </div>
        </div>
        <span className={`inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full ${toneClass}`}>
          <Icon size={20} strokeWidth={2.2} />
        </span>
      </div>
    </div>
  )
}

function GenderSelector({ value, onChange }) {
  return (
    <div className="grid grid-cols-2 gap-2">
      {genderOptions.map(({ value: optionValue, label, Icon }) => {
        const selected = value === optionValue

        return (
          <button
            key={optionValue}
            type="button"
            onClick={() => onChange(optionValue)}
            className={`flex min-h-12 items-center justify-center gap-2 rounded-[1rem] border px-3 py-3 text-sm font-semibold transition-all duration-300 ${
              selected
                ? 'border-[rgba(79,140,255,0.32)] bg-[rgba(79,140,255,0.1)] text-[var(--accent)] shadow-[0_10px_22px_rgba(79,140,255,0.12)]'
                : 'border-[rgba(62,82,130,0.08)] bg-white text-[var(--text-soft)] hover:border-[rgba(79,140,255,0.18)] hover:bg-[rgba(79,140,255,0.05)] hover:text-[var(--text)]'
            }`}
          >
            <Icon size={17} strokeWidth={2.2} />
            <span>{label}</span>
          </button>
        )
      })}
    </div>
  )
}

function BirthDatePicker({ value, open, onOpenChange, onChange }) {
  const selected = parseDateInput(value)

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => onOpenChange(!open)}
        className="flex w-full items-center justify-between gap-3 rounded-[1rem] border border-[rgba(62,82,130,0.08)] bg-white px-4 py-3 text-left text-sm text-[var(--text)] outline-none transition-all duration-300 hover:border-[rgba(79,140,255,0.24)] hover:bg-[rgba(79,140,255,0.03)]"
      >
        <span className={selected ? 'font-semibold text-[var(--text)]' : 'text-[var(--text-faint)]'}>
          {formatDisplayDate(value)}
        </span>
        <CalendarDays size={18} className="shrink-0 text-[var(--text-faint)]" strokeWidth={2.2} />
      </button>

      {open ? (
        <div className="absolute left-0 top-[calc(100%+0.6rem)] z-50 w-[min(21rem,calc(100vw-3rem))] rounded-[1.25rem] border border-[rgba(62,82,130,0.08)] bg-white p-3 shadow-[0_24px_56px_rgba(82,98,141,0.18)]">
          <DayPicker
            mode="single"
            selected={selected}
            captionLayout="dropdown"
            startMonth={new Date(1940, 0)}
            endMonth={new Date()}
            disabled={{ after: new Date() }}
            onSelect={(date) => {
              onChange(formatDateInput(date))
              onOpenChange(false)
            }}
            classNames={{
              root: 'text-sm text-[var(--text)]',
              months: 'space-y-3',
              month_caption: 'flex items-center justify-center pb-3',
              caption_label: 'text-sm font-semibold text-[var(--text)]',
              dropdowns: 'flex items-center justify-center gap-2',
              dropdown: 'rounded-full border border-[rgba(62,82,130,0.08)] bg-white px-2 py-1 text-sm outline-none',
              nav: 'flex items-center justify-between',
              button_previous: 'absolute left-3 top-3 inline-flex h-8 w-8 items-center justify-center rounded-full text-[var(--text-soft)] hover:bg-[rgba(56,75,121,0.06)]',
              button_next: 'absolute right-3 top-3 inline-flex h-8 w-8 items-center justify-center rounded-full text-[var(--text-soft)] hover:bg-[rgba(56,75,121,0.06)]',
              weekdays: 'grid grid-cols-7 gap-1 pb-1',
              weekday: 'h-8 text-center text-xs font-semibold text-[var(--text-faint)]',
              week: 'grid grid-cols-7 gap-1',
              day: 'h-9 w-9 p-0 text-center',
              day_button: 'h-9 w-9 rounded-full text-sm transition-colors hover:bg-[rgba(79,140,255,0.08)]',
              selected: 'text-white',
              today: 'font-bold text-[var(--accent)]',
              disabled: 'pointer-events-none opacity-30',
              outside: 'text-[var(--text-faint)] opacity-45',
            }}
            modifiersClassNames={{
              selected: '[&>button]:bg-[var(--accent)] [&>button]:text-white [&>button]:hover:bg-[var(--accent)]',
            }}
          />
        </div>
      ) : null}
    </div>
  )
}

function FieldLabel({ label, hint }) {
  return (
    <div className="mb-2">
      <p className="text-sm font-semibold text-[var(--text)]">{label}</p>
      {hint ? <p className="mt-1 text-xs leading-5 text-[var(--text-faint)]">{hint}</p> : null}
    </div>
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
  const [profileSettingsOpen, setProfileSettingsOpen] = useState(false)
  const [memorySettingsOpen, setMemorySettingsOpen] = useState(false)
  const [profileForm, setProfileForm] = useState(createEmptyProfileForm)
  const [profileInitialForm, setProfileInitialForm] = useState(createEmptyProfileForm)
  const [profileLoading, setProfileLoading] = useState(false)
  const [profileLoaded, setProfileLoaded] = useState(false)
  const [profileSaving, setProfileSaving] = useState(false)
  const [profileError, setProfileError] = useState('')
  const [profileSuccess, setProfileSuccess] = useState('')
  const [birthDatePickerOpen, setBirthDatePickerOpen] = useState(false)
  const [memoryForm, setMemoryForm] = useState(createEmptyMemoryForm)
  const [memoryInitialForm, setMemoryInitialForm] = useState(createEmptyMemoryForm)
  const [memoryRecords, setMemoryRecords] = useState({})
  const [memoryLoading, setMemoryLoading] = useState(false)
  const [memoryLoaded, setMemoryLoaded] = useState(false)
  const [memorySaving, setMemorySaving] = useState(false)
  const [memoryError, setMemoryError] = useState('')
  const [memorySuccess, setMemorySuccess] = useState('')
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
  const profileDirty = useMemo(
    () => JSON.stringify(profileForm) !== JSON.stringify(profileInitialForm),
    [profileForm, profileInitialForm],
  )
  const memoryDirty = useMemo(
    () => JSON.stringify(memoryForm) !== JSON.stringify(memoryInitialForm),
    [memoryForm, memoryInitialForm],
  )
  const activeMemoryRecords = useMemo(
    () =>
      memoryCategoryDefinitions
        .map((category) => ({
          ...category,
          records: category.fields
            .map((field) => {
              const fieldId = `${category.id}::${field.key}`
              const value = normalizeFormValue(memoryForm[fieldId])
              return value ? { fieldId, label: field.label, value } : null
            })
            .filter(Boolean),
        }))
        .filter((category) => category.records.length > 0),
    [memoryForm],
  )

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

  const resetProfileDraft = () => {
    setProfileForm(profileInitialForm)
    setProfileError('')
    setProfileSuccess('')
  }

  const resetMemoryDraft = () => {
    setMemoryForm(memoryInitialForm)
    setMemoryError('')
    setMemorySuccess('')
  }

  const discardProfileChanges = () => {
    setProfileForm(profileInitialForm)
    setProfileError('')
    setProfileSuccess('')
  }

  const discardMemoryChanges = () => {
    setMemoryForm(memoryInitialForm)
    setMemoryError('')
    setMemorySuccess('')
  }

  const confirmDiscardProfileChanges = () => {
    if (!profileDirty) {
      return true
    }

    const confirmed = window.confirm('当前有未保存的修改，确定放弃这些更改吗？')
    if (!confirmed) {
      return false
    }

    discardProfileChanges()
    return true
  }

  const confirmDiscardMemoryChanges = () => {
    if (!memoryDirty) {
      return true
    }

    const confirmed = window.confirm('当前有未保存的修改，确定放弃这些更改吗？')
    if (!confirmed) {
      return false
    }

    discardMemoryChanges()
    return true
  }

  const loadMemoryData = async () => {
    setMemoryLoading(true)
    setMemoryError('')
    setMemorySuccess('')

    try {
      const response = await fetch(`${apiBaseUrl}/memories/user-defined?user_id=${userId}&status=active`)
      if (!response.ok) {
        throw new Error(`自定义记忆加载失败: ${response.status}`)
      }

      const records = await response.json()
      const nextForm = mapMemoriesToForm(records)
      setMemoryRecords(buildMemoryRecordMap(records))
      setMemoryForm(nextForm)
      setMemoryInitialForm(nextForm)
      setMemoryLoaded(true)
    } catch (error) {
      setMemoryError(error instanceof Error ? error.message : '自定义记忆加载失败')
    } finally {
      setMemoryLoading(false)
    }
  }

  const openProfileSettingsPanel = () => {
    if (memorySettingsOpen && !confirmDiscardMemoryChanges()) {
      return
    }

    setMemorySettingsOpen(false)
    setProfileSettingsOpen(true)
    setProfileOpen(false)
  }

  const openMemorySettingsPanel = () => {
    if (profileSettingsOpen && !confirmDiscardProfileChanges()) {
      return
    }

    setProfileSettingsOpen(false)
    setMemorySettingsOpen(true)
    setProfileOpen(false)
  }

  const closeProfileSettingsPanel = () => {
    if (!confirmDiscardProfileChanges()) {
      return false
    }

    setProfileSettingsOpen(false)
    return true
  }

  const closeMemorySettingsPanel = () => {
    if (!confirmDiscardMemoryChanges()) {
      return false
    }

    setMemorySettingsOpen(false)
    return true
  }

  const handleProfileFieldChange = (name, value) => {
    setProfileForm((current) => ({ ...current, [name]: value }))
    setProfileError('')
    setProfileSuccess('')
  }

  const handleTrainingDayToggle = (day) => {
    setProfileForm((current) => ({
      ...current,
      preferred_training_days: current.preferred_training_days.includes(day)
        ? current.preferred_training_days.filter((item) => item !== day)
        : [...current.preferred_training_days, day],
    }))
    setProfileError('')
    setProfileSuccess('')
  }

  const handleMemoryFieldChange = (fieldId, value) => {
    setMemoryForm((current) => ({ ...current, [fieldId]: value }))
    setMemoryError('')
    setMemorySuccess('')
  }

  const validateProfileForm = () => {
    if (profileForm.birth_date) {
      const parsedDate = new Date(profileForm.birth_date)
      if (Number.isNaN(parsedDate.getTime())) {
        return '出生日期格式不正确'
      }
    }

    const numericFields = [
      ['height_cm', '身高'],
      ['weight_kg', '体重'],
      ['target_weight_kg', '目标体重'],
    ]

    for (const [fieldName, label] of numericFields) {
      const value = profileForm[fieldName]
      if (!value) {
        continue
      }

      const parsed = Number(value)
      if (!Number.isFinite(parsed) || parsed <= 0) {
        return `${label}必须是正数`
      }
    }

    return ''
  }

  const handleSaveProfile = async () => {
    const validationError = validateProfileForm()
    if (validationError) {
      setProfileError(validationError)
      setProfileSuccess('')
      return
    }

    setProfileSaving(true)
    setProfileError('')
    setProfileSuccess('')

    try {
      const response = await fetch(`${apiBaseUrl}/profiles/${userId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(serializeProfileForm(profileForm)),
      })
      if (!response.ok) {
        throw new Error(`个人信息保存失败: ${response.status}`)
      }

      const record = await response.json()
      const nextForm = mapProfileToForm(record)
      setProfileForm(nextForm)
      setProfileInitialForm(nextForm)
      setProfileLoaded(true)
      setProfileSuccess('个人信息已保存')
    } catch (error) {
      setProfileError(error instanceof Error ? error.message : '个人信息保存失败')
    } finally {
      setProfileSaving(false)
    }
  }

  const handleSaveMemory = async () => {
    setMemorySaving(true)
    setMemoryError('')
    setMemorySuccess('')

    try {
      const requests = []

      memoryCategoryDefinitions.forEach((category) => {
        category.fields.forEach((field) => {
          const fieldId = `${category.id}::${field.key}`
          const nextValue = normalizeFormValue(memoryForm[fieldId])
          const previousValue = normalizeFormValue(memoryInitialForm[fieldId])
          const existingRecord = memoryRecords[fieldId]

          if (!nextValue && !existingRecord) {
            return
          }

          if (nextValue === previousValue && ((nextValue && existingRecord) || (!nextValue && !existingRecord))) {
            return
          }

          if (nextValue && existingRecord) {
            requests.push(
              fetch(`${apiBaseUrl}/memories/user-defined/${existingRecord.id}`, {
                method: 'PATCH',
                headers: {
                  'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                  memory_value: nextValue,
                  raw_text: buildMemoryRawText(field.label, nextValue),
                  status: 'active',
                }),
              }),
            )
            return
          }

          if (nextValue && !existingRecord) {
            requests.push(
              fetch(`${apiBaseUrl}/memories/user-defined`, {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                  user_id: userId,
                  memory_key: field.key,
                  memory_category: category.id,
                  memory_value: nextValue,
                  raw_text: buildMemoryRawText(field.label, nextValue),
                  priority: 100,
                  status: 'active',
                }),
              }),
            )
            return
          }

          if (!nextValue && existingRecord) {
            requests.push(
              fetch(`${apiBaseUrl}/memories/user-defined/${existingRecord.id}`, {
                method: 'PATCH',
                headers: {
                  'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                  memory_value: null,
                  raw_text: null,
                  status: 'archived',
                }),
              }),
            )
            return
          }
        })
      })

      const responses = await Promise.all(requests)
      const failed = responses.find((response) => !response.ok)
      if (failed) {
        throw new Error(`自定义记忆保存失败: ${failed.status}`)
      }

      await loadMemoryData()
      setMemorySuccess('自定义记忆已保存')
    } catch (error) {
      setMemoryError(error instanceof Error ? error.message : '自定义记忆保存失败')
    } finally {
      setMemorySaving(false)
    }
  }

  useEffect(() => {
    if (!profileSettingsOpen || profileLoaded) {
      return
    }

    let cancelled = false

    const run = async () => {
      setProfileLoading(true)
      setProfileError('')
      setProfileSuccess('')

      try {
        const response = await fetch(`${apiBaseUrl}/profiles/${userId}`)
        if (!response.ok) {
          throw new Error(`个人信息加载失败: ${response.status}`)
        }

        const record = await response.json()
        if (cancelled) {
          return
        }

        const nextForm = mapProfileToForm(record)
        setProfileForm(nextForm)
        setProfileInitialForm(nextForm)
        setProfileLoaded(true)
      } catch (error) {
        if (!cancelled) {
          setProfileError(error instanceof Error ? error.message : '个人信息加载失败')
        }
      } finally {
        if (!cancelled) {
          setProfileLoading(false)
        }
      }
    }

    void run()

    return () => {
      cancelled = true
    }
  }, [profileSettingsOpen, profileLoaded, userId])

  useEffect(() => {
    if (!memorySettingsOpen || memoryLoaded || memoryLoading) {
      return
    }

    let cancelled = false

    const run = async () => {
      setMemoryLoading(true)
      setMemoryError('')
      setMemorySuccess('')

      try {
        const response = await fetch(`${apiBaseUrl}/memories/user-defined?user_id=${userId}&status=active`)
        if (!response.ok) {
          throw new Error(`自定义记忆加载失败: ${response.status}`)
        }

        const records = await response.json()
        if (cancelled) {
          return
        }

        const nextForm = mapMemoriesToForm(records)
        setMemoryRecords(buildMemoryRecordMap(records))
        setMemoryForm(nextForm)
        setMemoryInitialForm(nextForm)
        setMemoryLoaded(true)
      } catch (error) {
        if (!cancelled) {
          setMemoryError(error instanceof Error ? error.message : '自定义记忆加载失败')
        }
      } finally {
        if (!cancelled) {
          setMemoryLoading(false)
        }
      }
    }

    void run()

    return () => {
      cancelled = true
    }
  }, [memorySettingsOpen, memoryLoaded, memoryLoading, userId])

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
    setProfileOpen(false)
    if (profileSettingsOpen) {
      closeProfileSettingsPanel()
      return
    }
    if (memorySettingsOpen) {
      closeMemorySettingsPanel()
      return
    }
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
                  openProfileSettingsPanel()
                }}
                className="block w-full rounded-[1rem] px-3 py-3 text-left text-sm font-medium text-[var(--text)] transition-all duration-300 hover:bg-[rgba(52,74,140,0.05)]"
              >
                个人信息
              </button>
              <button
                type="button"
                onClick={() => {
                  openMemorySettingsPanel()
                }}
                className="block w-full rounded-[1rem] px-3 py-3 text-left text-sm font-medium text-[var(--text)] transition-all duration-300 hover:bg-[rgba(52,74,140,0.05)]"
              >
                自定义记忆
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
          sidebarOpen || profileSettingsOpen || memorySettingsOpen || profileOpen
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
        className={`fixed inset-y-0 right-0 z-40 w-[min(100vw,44rem)] transform bg-[rgba(255,255,255,0.9)] px-3 py-3 shadow-[-14px_0_50px_rgba(82,98,141,0.08)] backdrop-blur-2xl transition-all duration-300 ease-in-out sm:px-4 sm:py-4 ${
          profileSettingsOpen ? 'translate-x-0' : 'translate-x-[110%]'
        }`}
      >
        <div className="flex h-full min-h-0 flex-col rounded-[1.4rem] bg-[rgba(255,255,255,0.66)] px-4 py-4 sm:px-5 sm:py-5">
          <div className="shrink-0">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-[var(--text-faint)]">
                  Profile
                </p>
                <h3 className="mt-2 font-display text-[1.7rem] leading-none text-[var(--text)] sm:text-[2rem]">
                  个人信息
                </h3>
                <p className="mt-3 text-sm leading-6 text-[var(--text-soft)]">
                  维护你的基础资料、训练目标和饮食背景。
                </p>
              </div>
              <button
                type="button"
                onClick={closeProfileSettingsPanel}
                className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-[var(--text-faint)] transition-all duration-300 hover:bg-[rgba(46,56,87,0.06)] hover:text-[var(--text)]"
                aria-label="关闭个人信息"
              >
                ×
              </button>
            </div>

            <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2">
              {getProfileSummaryItems(profileForm).map((item) => (
                <ProfileMetricCard key={item.label} item={item} />
              ))}
            </div>
          </div>

          <div className="app-scrollbar mt-5 min-h-0 flex-1 overflow-y-auto pb-4 pr-1">
            <div className="space-y-5">
              {profileError ? (
                <div className="rounded-[1rem] bg-[rgba(215,99,99,0.08)] px-4 py-3 text-sm text-[var(--danger)]">
                  {profileError}
                </div>
              ) : null}
              {profileSuccess ? (
                <div className="rounded-[1rem] bg-[rgba(119,199,176,0.12)] px-4 py-3 text-sm text-[#3f8f79]">
                  {profileSuccess}
                </div>
              ) : null}
              {profileLoading ? (
                <div className="rounded-[1rem] bg-[rgba(79,140,255,0.08)] px-4 py-3 text-sm text-[var(--accent)]">
                  正在加载个人信息...
                </div>
              ) : null}
                  <section className="rounded-[1rem] bg-[rgba(255,255,255,0.78)] px-4 py-4 shadow-[0_8px_24px_rgba(96,110,150,0.06)]">
                    <FieldLabel label="基础资料" hint="这些信息会帮助助手更准确理解你的身体背景。" />
                    <div className="grid gap-4 sm:grid-cols-2">
                      <div>
                        <FieldLabel label="性别" />
                        <GenderSelector
                          value={profileForm.gender}
                          onChange={(value) => handleProfileFieldChange('gender', value)}
                        />
                      </div>
                      <div>
                        <FieldLabel label="出生日期" />
                        <BirthDatePicker
                          value={profileForm.birth_date}
                          open={birthDatePickerOpen}
                          onOpenChange={setBirthDatePickerOpen}
                          onChange={(value) => handleProfileFieldChange('birth_date', value)}
                        />
                      </div>
                      <label>
                        <FieldLabel label="身高 (cm)" />
                        <input type="number" min="0" step="0.1" value={profileForm.height_cm} onChange={(event) => handleProfileFieldChange('height_cm', event.target.value)} className="w-full rounded-[1rem] border border-[rgba(62,82,130,0.08)] bg-white px-4 py-3 text-sm text-[var(--text)] outline-none" />
                      </label>
                      <label>
                        <FieldLabel label="体重 (kg)" />
                        <input type="number" min="0" step="0.1" value={profileForm.weight_kg} onChange={(event) => handleProfileFieldChange('weight_kg', event.target.value)} className="w-full rounded-[1rem] border border-[rgba(62,82,130,0.08)] bg-white px-4 py-3 text-sm text-[var(--text)] outline-none" />
                      </label>
                    </div>
                  </section>

                  <section className="rounded-[1rem] bg-[rgba(255,255,255,0.78)] px-4 py-4 shadow-[0_8px_24px_rgba(96,110,150,0.06)]">
                    <FieldLabel label="目标与训练" hint="这里会影响训练建议和长期对话上下文。" />
                    <div className="grid gap-4 sm:grid-cols-2">
                      <label>
                        <FieldLabel label="目标体重 (kg)" />
                        <input type="number" min="0" step="0.1" value={profileForm.target_weight_kg} onChange={(event) => handleProfileFieldChange('target_weight_kg', event.target.value)} className="w-full rounded-[1rem] border border-[rgba(62,82,130,0.08)] bg-white px-4 py-3 text-sm text-[var(--text)] outline-none" />
                      </label>
                      <label>
                        <FieldLabel label="训练目标" />
                        <select value={profileForm.goal_type} onChange={(event) => handleProfileFieldChange('goal_type', event.target.value)} className="w-full rounded-[1rem] border border-[rgba(62,82,130,0.08)] bg-white px-4 py-3 text-sm text-[var(--text)] outline-none">
                          <option value="">请选择</option>
                          {goalTypeOptions.map((option) => (
                            <option key={option} value={option}>{option}</option>
                          ))}
                        </select>
                      </label>
                      <label>
                        <FieldLabel label="训练水平" />
                        <select value={profileForm.training_level} onChange={(event) => handleProfileFieldChange('training_level', event.target.value)} className="w-full rounded-[1rem] border border-[rgba(62,82,130,0.08)] bg-white px-4 py-3 text-sm text-[var(--text)] outline-none">
                          <option value="">请选择</option>
                          {trainingLevelOptions.map((option) => (
                            <option key={option} value={option}>{option}</option>
                          ))}
                        </select>
                      </label>
                      <div>
                        <FieldLabel label="偏好训练日" hint="多选后会按逗号字符串写入当前表结构。" />
                        <WeekdaySelector value={profileForm.preferred_training_days} onToggle={handleTrainingDayToggle} />
                      </div>
                    </div>
                  </section>

                  <section className="rounded-[1rem] bg-[rgba(255,255,255,0.78)] px-4 py-4 shadow-[0_8px_24px_rgba(96,110,150,0.06)]">
                    <FieldLabel label="限制与饮食" hint="用来告诉助手你的伤病、医疗和饮食背景。" />
                    <div className="grid gap-4">
                      <label>
                        <FieldLabel label="伤病说明" />
                        <textarea rows="3" value={profileForm.injury_notes} onChange={(event) => handleProfileFieldChange('injury_notes', event.target.value)} className="w-full rounded-[1rem] border border-[rgba(62,82,130,0.08)] bg-white px-4 py-3 text-sm leading-6 text-[var(--text)] outline-none" />
                      </label>
                      <label>
                        <FieldLabel label="医疗说明" />
                        <textarea rows="3" value={profileForm.medical_notes} onChange={(event) => handleProfileFieldChange('medical_notes', event.target.value)} className="w-full rounded-[1rem] border border-[rgba(62,82,130,0.08)] bg-white px-4 py-3 text-sm leading-6 text-[var(--text)] outline-none" />
                      </label>
                      <label>
                        <FieldLabel label="饮食偏好" />
                        <textarea rows="3" value={profileForm.diet_preference} onChange={(event) => handleProfileFieldChange('diet_preference', event.target.value)} className="w-full rounded-[1rem] border border-[rgba(62,82,130,0.08)] bg-white px-4 py-3 text-sm leading-6 text-[var(--text)] outline-none" />
                      </label>
                    </div>
                  </section>

                  <section className="rounded-[1rem] bg-[rgba(255,255,255,0.78)] px-4 py-4 shadow-[0_8px_24px_rgba(96,110,150,0.06)]">
                    <label>
                      <FieldLabel label="补充备注" hint="可以写你的作息、训练偏好补充或其他想长期保留的信息。" />
                      <textarea rows="4" value={profileForm.remark} onChange={(event) => handleProfileFieldChange('remark', event.target.value)} className="w-full rounded-[1rem] border border-[rgba(62,82,130,0.08)] bg-white px-4 py-3 text-sm leading-6 text-[var(--text)] outline-none" />
                    </label>
                  </section>
            </div>
          </div>

          <div className="shrink-0 border-t border-[rgba(62,82,130,0.08)] pt-4">
            <div className="flex items-center justify-between gap-3">
              <button type="button" onClick={resetProfileDraft} disabled={!profileDirty || profileSaving} className="rounded-full bg-[rgba(56,75,121,0.06)] px-4 py-2 text-sm font-semibold text-[var(--text-soft)] transition-all duration-300 hover:bg-[rgba(56,75,121,0.1)] hover:text-[var(--text)] disabled:cursor-not-allowed disabled:opacity-50">
                还原修改
              </button>
              <button type="button" onClick={handleSaveProfile} disabled={profileSaving || profileLoading} className="rounded-full bg-[linear-gradient(135deg,#5f89ff,#76d0b5)] px-5 py-2.5 text-sm font-semibold text-white shadow-[0_12px_24px_rgba(98,134,255,0.2)] transition-all duration-300 hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-60">
                {profileSaving ? '保存中...' : '保存个人信息'}
              </button>
            </div>
          </div>
        </div>
      </aside>

      <aside
        className={`fixed inset-y-0 right-0 z-40 w-[min(100vw,52rem)] transform bg-[rgba(255,255,255,0.9)] px-3 py-3 shadow-[-14px_0_50px_rgba(82,98,141,0.08)] backdrop-blur-2xl transition-all duration-300 ease-in-out sm:px-4 sm:py-4 ${
          memorySettingsOpen ? 'translate-x-0' : 'translate-x-[110%]'
        }`}
      >
        <div className="flex h-full min-h-0 flex-col rounded-[1.4rem] bg-[rgba(255,255,255,0.66)] px-4 py-4 sm:px-5 sm:py-5">
          <div className="shrink-0">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-[var(--text-faint)]">
                  Memory
                </p>
                <h3 className="mt-2 font-display text-[1.7rem] leading-none text-[var(--text)] sm:text-[2rem]">
                  自定义记忆
                </h3>
                <p className="mt-3 text-sm leading-6 text-[var(--text-soft)]">
                  维护你希望 FitMind 长期记住的显式偏好。
                </p>
              </div>
              <button type="button" onClick={closeMemorySettingsPanel} className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-[var(--text-faint)] transition-all duration-300 hover:bg-[rgba(46,56,87,0.06)] hover:text-[var(--text)]" aria-label="关闭自定义记忆">
                ×
              </button>
            </div>

            <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
              {[
                { label: '已激活', value: `${activeMemoryRecords.reduce((total, category) => total + category.records.length, 0)} 条` },
                { label: '类别数', value: `${activeMemoryRecords.length || 0} 类` },
                { label: '风格', value: normalizeFormValue(memoryForm['conversation_preference::response_style']) || '未设置' },
              ].map((item) => (
                <div key={item.label} className="rounded-[1rem] bg-[rgba(85,104,170,0.04)] px-4 py-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[var(--text-faint)]">
                    {item.label}
                  </p>
                  <p className="mt-2 text-sm font-semibold text-[var(--text)]">{item.value}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="app-scrollbar mt-5 min-h-0 flex-1 overflow-y-auto pb-4 pr-1">
            <div className="space-y-5">
              {memoryError ? (
                <div className="rounded-[1rem] bg-[rgba(215,99,99,0.08)] px-4 py-3 text-sm text-[var(--danger)]">
                  {memoryError}
                </div>
              ) : null}
              {memorySuccess ? (
                <div className="rounded-[1rem] bg-[rgba(119,199,176,0.12)] px-4 py-3 text-sm text-[#3f8f79]">
                  {memorySuccess}
                </div>
              ) : null}
              {memoryLoading ? (
                <div className="space-y-3">
                  <div className="skeleton-shimmer h-24 rounded-[1rem]" />
                  <div className="skeleton-shimmer h-24 rounded-[1rem]" />
                  <div className="skeleton-shimmer h-24 rounded-[1rem]" />
                </div>
              ) : (
                <>
                  {activeMemoryRecords.length ? (
                    <section className="grid gap-3 sm:grid-cols-2">
                      {activeMemoryRecords.map((category) => (
                        <article key={category.id} className="rounded-[1rem] bg-[rgba(255,255,255,0.78)] px-4 py-4 shadow-[0_8px_24px_rgba(96,110,150,0.06)]">
                          <p className="text-sm font-semibold text-[var(--text)]">{category.title}</p>
                          <div className="mt-3 space-y-2">
                            {category.records.map((record) => (
                              <div key={record.fieldId}>
                                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--text-faint)]">
                                  {record.label}
                                </p>
                                <p className="mt-1 text-sm leading-6 text-[var(--text-soft)]">{record.value}</p>
                              </div>
                            ))}
                          </div>
                        </article>
                      ))}
                    </section>
                  ) : (
                    <article className="rounded-[1rem] bg-[rgba(255,255,255,0.78)] px-4 py-4 shadow-[0_8px_24px_rgba(96,110,150,0.06)]">
                      <p className="text-sm font-semibold text-[var(--text)]">还没有激活的自定义记忆</p>
                      <p className="mt-2 text-sm leading-7 text-[var(--text-soft)]">
                        你可以从下面的结构化表单开始填写，保存后 FitMind 会长期记住这些偏好。
                      </p>
                    </article>
                  )}

                  {memoryCategoryDefinitions.map((category) => (
                    <section key={category.id} className="rounded-[1rem] bg-[rgba(255,255,255,0.78)] px-4 py-4 shadow-[0_8px_24px_rgba(96,110,150,0.06)]">
                      <FieldLabel label={category.title} hint={category.description} />
                      <div className="grid gap-4 sm:grid-cols-2">
                        {category.fields.map((field) => {
                          const fieldId = `${category.id}::${field.key}`

                          if (field.type === 'select') {
                            return (
                              <label key={fieldId}>
                                <FieldLabel label={field.label} />
                                <select value={memoryForm[fieldId]} onChange={(event) => handleMemoryFieldChange(fieldId, event.target.value)} className="w-full rounded-[1rem] border border-[rgba(62,82,130,0.08)] bg-white px-4 py-3 text-sm text-[var(--text)] outline-none">
                                  <option value="">请选择</option>
                                  {field.options.map((option) => (
                                    <option key={option} value={option}>{option}</option>
                                  ))}
                                </select>
                              </label>
                            )
                          }

                          if (field.type === 'radio') {
                            return (
                              <div key={fieldId} className="sm:col-span-2">
                                <FieldLabel label={field.label} />
                                <div className="flex flex-wrap gap-2">
                                  {field.options.map((option) => {
                                    const selected = memoryForm[fieldId] === option

                                    return (
                                      <button key={option} type="button" onClick={() => handleMemoryFieldChange(fieldId, option)} className={`rounded-full px-3 py-2 text-sm font-medium transition-all duration-300 ${selected ? 'bg-[rgba(79,140,255,0.12)] text-[var(--accent)]' : 'bg-[rgba(56,75,121,0.05)] text-[var(--text-soft)] hover:bg-[rgba(56,75,121,0.09)] hover:text-[var(--text)]'}`}>
                                        {option}
                                      </button>
                                    )
                                  })}
                                </div>
                              </div>
                            )
                          }

                          return (
                            <label key={fieldId}>
                              <FieldLabel label={field.label} />
                              <textarea rows={field.rows ?? 3} value={memoryForm[fieldId]} onChange={(event) => handleMemoryFieldChange(fieldId, event.target.value)} className="w-full rounded-[1rem] border border-[rgba(62,82,130,0.08)] bg-white px-4 py-3 text-sm leading-6 text-[var(--text)] outline-none" />
                            </label>
                          )
                        })}
                      </div>
                    </section>
                  ))}
                </>
              )}
            </div>
          </div>

          <div className="shrink-0 border-t border-[rgba(62,82,130,0.08)] pt-4">
            <div className="flex items-center justify-between gap-3">
              <button type="button" onClick={resetMemoryDraft} disabled={!memoryDirty || memorySaving} className="rounded-full bg-[rgba(56,75,121,0.06)] px-4 py-2 text-sm font-semibold text-[var(--text-soft)] transition-all duration-300 hover:bg-[rgba(56,75,121,0.1)] hover:text-[var(--text)] disabled:cursor-not-allowed disabled:opacity-50">
                还原修改
              </button>
              <button type="button" onClick={handleSaveMemory} disabled={memorySaving || memoryLoading} className="rounded-full bg-[linear-gradient(135deg,#5f89ff,#76d0b5)] px-5 py-2.5 text-sm font-semibold text-white shadow-[0_12px_24px_rgba(98,134,255,0.2)] transition-all duration-300 hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-60">
                {memorySaving ? '保存中...' : '保存自定义记忆'}
              </button>
            </div>
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
