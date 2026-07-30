import { useEffect, useState } from 'react'
import {
  ArrowLeft,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Dumbbell,
  Filter,
  Gauge,
  Search,
  Sparkles,
} from 'lucide-react'

const apiBaseUrl =
  import.meta.env.VITE_AGENT_BASE_URL?.replace(/\/$/, '') ?? 'http://127.0.0.1:8000/api/v1'

const muscleGroups = [
  { value: '', label: '全部' },
  { value: 'chest', label: '胸' },
  { value: 'back', label: '背' },
  { value: 'legs', label: '腿' },
  { value: 'shoulders', label: '肩' },
  { value: 'arms', label: '手臂' },
  { value: 'core', label: '核心' },
  { value: 'full_body', label: '全身' },
  { value: 'cardio', label: '有氧' },
  { value: 'other', label: '其他' },
]

const statusLabels = {
  completed: '已完成',
  partial: '部分完成',
  skipped: '已跳过',
}

function toInputDate(value) {
  const date = new Date(value)
  const offset = date.getTimezoneOffset() * 60000
  return new Date(date.getTime() - offset).toISOString().slice(0, 10)
}

function createDefaultFilters() {
  const endDate = new Date()
  const startDate = new Date()
  startDate.setDate(startDate.getDate() - 6)
  return {
    start_date: toInputDate(startDate),
    end_date: toInputDate(endDate),
    muscle_group: '',
    exercise_keyword: '',
  }
}

function formatDate(value) {
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'long',
    day: 'numeric',
    weekday: 'short',
  }).format(new Date(`${value}T00:00:00`))
}

function formatExercise(item) {
  const parts = [
    item.sets_count ? `${item.sets_count} 组` : null,
    item.reps_text,
    item.weight_text,
    item.duration_text,
    item.distance_text,
  ].filter(Boolean)
  return parts.length ? parts.join(' · ') : '已记录动作'
}

async function requestWorkoutHistory(userId, filters, page) {
  const query = new URLSearchParams({
    user_id: String(userId),
    start_date: filters.start_date,
    end_date: filters.end_date,
    page: String(page),
    page_size: '20',
  })
  if (filters.muscle_group) query.set('muscle_group', filters.muscle_group)
  if (filters.exercise_keyword.trim()) query.set('exercise_keyword', filters.exercise_keyword.trim())

  const response = await fetch(`${apiBaseUrl}/workouts/history?${query.toString()}`)
  const payload = await response.json()
  if (!response.ok) throw new Error(payload.detail ?? `请求失败: ${response.status}`)
  return payload
}

function SummaryCard({ label, value, hint, Icon, tone = 'blue' }) {
  const toneClass = tone === 'mint'
    ? 'bg-[rgba(119,199,176,0.14)] text-[#398b73]'
    : 'bg-[rgba(79,140,255,0.1)] text-[var(--accent)]'

  return (
    <article className="lift-card rounded-[1.35rem] border border-[rgba(33,52,48,0.05)] bg-[rgba(255,255,255,0.74)] p-4 shadow-[0_12px_30px_rgba(97,119,112,0.06)] backdrop-blur-xl">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-[var(--text-faint)]">{label}</p>
          <p className="mt-2 text-2xl font-extrabold tracking-[-0.05em] text-[var(--text)]">{value}</p>
          <p className="mt-1 text-xs text-[var(--text-faint)]">{hint}</p>
        </div>
        <span className={`inline-flex h-10 w-10 items-center justify-center rounded-full ${toneClass}`}>
          <Icon size={18} strokeWidth={2.3} />
        </span>
      </div>
    </article>
  )
}

function HistorySkeleton() {
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {[1, 2, 3, 4].map((item) => <div key={item} className="skeleton-shimmer h-32 rounded-[1.35rem]" />)}
      </div>
      {[1, 2].map((item) => <div key={item} className="skeleton-shimmer h-48 rounded-[1.5rem]" />)}
    </div>
  )
}

function WorkoutHistory({ session, onBackToChat }) {
  const userId = session.userId ?? 1
  const [filters, setFilters] = useState(createDefaultFilters)
  const [history, setHistory] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadHistory = async (nextPage = 1, nextFilters = filters) => {
    setLoading(true)
    setError('')
    try {
      setHistory(await requestWorkoutHistory(userId, nextFilters, nextPage))
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : '训练历史加载失败')
      setHistory(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let cancelled = false
    const initialFilters = createDefaultFilters()

    void requestWorkoutHistory(userId, initialFilters, 1)
      .then((payload) => {
        if (!cancelled) setHistory(payload)
      })
      .catch((requestError) => {
        if (!cancelled) {
          setError(requestError instanceof Error ? requestError.message : '训练历史加载失败')
          setHistory(null)
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [userId])

  const handleSubmit = (event) => {
    event.preventDefault()
    void loadHistory(1)
  }

  const handleReset = () => {
    const nextFilters = createDefaultFilters()
    setFilters(nextFilters)
    void loadHistory(1, nextFilters)
  }

  const summary = history?.summary
  const pagination = history?.pagination

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#f8faf8] text-[var(--text)]">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_10%_0%,rgba(79,140,255,0.12),transparent_24%),radial-gradient(circle_at_90%_8%,rgba(119,199,176,0.14),transparent_22%),linear-gradient(180deg,#fbfdfc_0%,#f3f7f4_100%)]" />
      <div className="soft-grid pointer-events-none absolute inset-x-0 top-0 h-80 opacity-60" />

      <section className="relative mx-auto w-[min(94vw,1240px)] pb-14 pt-7 sm:pt-10">
        <header className="fade-up flex flex-wrap items-start justify-between gap-5">
          <div className="flex items-start gap-4">
            <button
              type="button"
              onClick={onBackToChat}
              className="mt-1 inline-flex h-11 w-11 items-center justify-center rounded-full border border-[rgba(33,52,48,0.07)] bg-white/80 text-[var(--text-soft)] shadow-[0_10px_28px_rgba(91,112,105,0.08)] transition-all duration-300 hover:-translate-x-0.5 hover:text-[var(--text)]"
              aria-label="返回聊天"
            >
              <ArrowLeft size={19} />
            </button>
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[0.3em] text-[var(--text-faint)]">Training Archive</p>
              <h1 className="mt-2 font-display text-[2.4rem] leading-none tracking-[-0.055em] text-[var(--text)] sm:text-[3.1rem]">训练历史</h1>
              <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--text-soft)]">把每一次完成都留在可回顾的轨迹里。</p>
            </div>
          </div>
          <div className="rounded-full border border-[rgba(33,52,48,0.06)] bg-white/70 px-4 py-2 text-xs font-semibold text-[var(--text-soft)] shadow-[0_8px_22px_rgba(91,112,105,0.06)]">
            最多查询 90 天
          </div>
        </header>

        <form onSubmit={handleSubmit} className="fade-up-delayed glass-panel subtle-ring mt-8 rounded-[1.7rem] p-4 shadow-[0_18px_50px_rgba(100,122,113,0.09)] sm:p-5">
          <div className="flex items-center gap-2 text-sm font-bold text-[var(--text)]">
            <Filter size={17} className="text-[var(--accent)]" />
            查询条件
          </div>
          <div className="mt-4 grid gap-3 lg:grid-cols-[1fr_1fr_1.4fr_auto]">
            <label className="rounded-[1rem] bg-[rgba(39,65,59,0.035)] px-3 py-2.5">
              <span className="text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--text-faint)]">开始日期</span>
              <input type="date" value={filters.start_date} max={filters.end_date} onChange={(event) => setFilters((current) => ({ ...current, start_date: event.target.value }))} className="mt-1 block w-full bg-transparent text-sm font-semibold text-[var(--text)] outline-none" />
            </label>
            <label className="rounded-[1rem] bg-[rgba(39,65,59,0.035)] px-3 py-2.5">
              <span className="text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--text-faint)]">结束日期</span>
              <input type="date" value={filters.end_date} min={filters.start_date} max={toInputDate(new Date())} onChange={(event) => setFilters((current) => ({ ...current, end_date: event.target.value }))} className="mt-1 block w-full bg-transparent text-sm font-semibold text-[var(--text)] outline-none" />
            </label>
            <label className="flex items-center gap-3 rounded-[1rem] bg-[rgba(39,65,59,0.035)] px-3 py-2.5">
              <Search size={18} className="shrink-0 text-[var(--text-faint)]" />
              <input value={filters.exercise_keyword} onChange={(event) => setFilters((current) => ({ ...current, exercise_keyword: event.target.value }))} placeholder="动作名称，如卧推" className="min-w-0 flex-1 bg-transparent text-sm font-semibold text-[var(--text)] outline-none placeholder:font-medium placeholder:text-[var(--text-faint)]" />
            </label>
            <div className="flex gap-2">
              <button type="button" onClick={handleReset} className="rounded-full px-4 text-sm font-semibold text-[var(--text-soft)] transition-colors hover:bg-[rgba(33,52,48,0.05)]">重置</button>
              <button type="submit" disabled={loading} className="rounded-full bg-[linear-gradient(135deg,#5f89ff,#76cdb2)] px-5 text-sm font-semibold text-white shadow-[0_12px_24px_rgba(96,139,255,0.22)] transition-all duration-300 hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-60">查询</button>
            </div>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {muscleGroups.map((item) => {
              const selected = filters.muscle_group === item.value
              return <button key={item.value || 'all'} type="button" onClick={() => setFilters((current) => ({ ...current, muscle_group: item.value }))} className={`rounded-full px-3.5 py-2 text-xs font-bold transition-all duration-300 ${selected ? 'bg-[rgba(79,140,255,0.13)] text-[var(--accent)] shadow-[0_6px_18px_rgba(79,140,255,0.1)]' : 'bg-[rgba(33,52,48,0.04)] text-[var(--text-soft)] hover:bg-[rgba(33,52,48,0.08)]'}`}>{item.label}</button>
            })}
          </div>
        </form>

        <section className="mt-5">
          {loading ? <HistorySkeleton /> : null}
          {!loading && error ? <div className="rounded-[1.4rem] border border-[rgba(215,99,99,0.16)] bg-[rgba(255,250,250,0.85)] px-5 py-5 text-sm leading-7 text-[var(--danger)]">训练历史暂时无法加载：{error}</div> : null}
          {!loading && !error && history ? <>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <SummaryCard label="训练记录" value={`${summary.record_count} 次`} hint={`覆盖 ${summary.training_day_count} 天`} Icon={Dumbbell} />
              <SummaryCard label="完成状态" value={`${summary.completed_record_count} 次`} hint="已完成训练" Icon={Sparkles} tone="mint" />
              <SummaryCard label="已知时长" value={summary.total_duration_minutes == null ? '未记录' : `${summary.total_duration_minutes} 分`} hint="仅统计已填写时长" Icon={Clock3} />
              <SummaryCard label="训练容量" value={`${summary.strength_sets_count} 组`} hint={`有氧动作 ${summary.cardio_item_count} 项`} Icon={Gauge} tone="mint" />
            </div>

            <div className="mt-7 flex items-center justify-between gap-4">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.25em] text-[var(--text-faint)]">Timeline</p>
                <h2 className="mt-1 font-display text-[2rem] leading-none tracking-[-0.045em] text-[var(--text)]">训练时间线</h2>
              </div>
              <p className="text-xs font-semibold text-[var(--text-faint)]">共 {pagination.total_records} 条记录</p>
            </div>

            {history.records.length ? <div className="mt-4 space-y-4">
              {history.records.map((record, index) => <article key={record.id} className="fade-up relative overflow-hidden rounded-[1.55rem] border border-[rgba(33,52,48,0.055)] bg-[rgba(255,255,255,0.76)] p-5 shadow-[0_14px_36px_rgba(98,119,112,0.07)]" style={{ animationDelay: `${index * 50}ms` }}>
                <div className="absolute left-0 top-0 h-full w-1 bg-[linear-gradient(180deg,#78cdb4,#7195ff)]" />
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2 text-sm font-bold text-[var(--text)]"><CalendarDays size={16} className="text-[var(--accent)]" />{formatDate(record.record_date)}</div>
                    <h3 className="mt-3 text-lg font-extrabold tracking-[-0.025em] text-[var(--text)]">{record.session_name || '未命名训练'}</h3>
                  </div>
                  <span className={`rounded-full px-3 py-1.5 text-xs font-bold ${record.completion_status === 'completed' ? 'bg-[rgba(119,199,176,0.14)] text-[#398b73]' : 'bg-[rgba(224,166,85,0.13)] text-[#a96e16]'}`}>{statusLabels[record.completion_status] ?? record.completion_status}</span>
                </div>
                <div className="mt-4 flex flex-wrap gap-2 text-xs font-semibold text-[var(--text-soft)]">
                  {record.duration_minutes ? <span className="rounded-full bg-[rgba(33,52,48,0.045)] px-3 py-1.5">{record.duration_minutes} 分钟</span> : null}
                  {record.perceived_exertion ? <span className="rounded-full bg-[rgba(33,52,48,0.045)] px-3 py-1.5">RPE {record.perceived_exertion}</span> : null}
                  {record.energy_level ? <span className="rounded-full bg-[rgba(33,52,48,0.045)] px-3 py-1.5">能量 {record.energy_level}/10</span> : null}
                  {record.mood ? <span className="rounded-full bg-[rgba(33,52,48,0.045)] px-3 py-1.5">{record.mood}</span> : null}
                </div>
                <div className="mt-5 divide-y divide-[rgba(33,52,48,0.055)] rounded-[1rem] bg-[rgba(247,250,248,0.85)] px-4">
                  {record.items.length ? record.items.map((item) => <div key={`${record.id}-${item.exercise_name}`} className="flex items-center justify-between gap-4 py-3.5"><div><p className="text-sm font-bold text-[var(--text)]">{item.exercise_name}</p><p className="mt-1 text-xs text-[var(--text-faint)]">{item.muscle_groups.join(' · ')}</p></div><p className="text-right text-xs font-semibold leading-5 text-[var(--text-soft)]">{formatExercise(item)}</p></div>) : <p className="py-3.5 text-sm leading-6 text-[var(--text-soft)]">{record.raw_text}</p>}
                </div>
              </article>)}
            </div> : <div className="mt-4 rounded-[1.55rem] border border-dashed border-[rgba(33,52,48,0.13)] bg-white/55 px-6 py-14 text-center"><Dumbbell className="mx-auto text-[var(--text-faint)]" size={28} /><h3 className="mt-4 text-base font-bold text-[var(--text)]">这个范围内还没有训练记录</h3><p className="mx-auto mt-2 max-w-md text-sm leading-6 text-[var(--text-soft)]">换个日期、部位或动作试试。训练完成后，也可以直接在聊天里告诉 FitMind。</p></div>}

            {pagination.total_pages > 1 ? <div className="mt-7 flex items-center justify-center gap-3"><button type="button" disabled={pagination.page <= 1 || loading} onClick={() => void loadHistory(pagination.page - 1)} className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-white text-[var(--text-soft)] shadow-[0_8px_20px_rgba(91,112,105,0.08)] disabled:opacity-40"><ChevronLeft size={18} /></button><span className="text-sm font-bold text-[var(--text-soft)]">第 {pagination.page} / {pagination.total_pages} 页</span><button type="button" disabled={pagination.page >= pagination.total_pages || loading} onClick={() => void loadHistory(pagination.page + 1)} className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-white text-[var(--text-soft)] shadow-[0_8px_20px_rgba(91,112,105,0.08)] disabled:opacity-40"><ChevronRight size={18} /></button></div> : null}
          </> : null}
        </section>
      </section>
    </main>
  )
}

export default WorkoutHistory
