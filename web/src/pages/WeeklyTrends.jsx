import { useEffect, useState } from 'react'
import {
  Activity,
  ArrowLeft,
  CalendarRange,
  ChevronLeft,
  ChevronRight,
  Dumbbell,
  Flame,
  MoonStar,
  RefreshCw,
  Sparkles,
  Utensils,
} from 'lucide-react'
import {
  Area,
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

const apiBaseUrl =
  import.meta.env.VITE_AGENT_BASE_URL?.replace(/\/$/, '') ?? 'http://127.0.0.1:8000/api/v1'

const chartColors = {
  current: '#4f8cff',
  previous: '#b8c2bf',
  mint: '#54b99c',
  amber: '#e4a853',
}

function toInputDate(value) {
  const date = new Date(value)
  const offset = date.getTimezoneOffset() * 60000
  return new Date(date.getTime() - offset).toISOString().slice(0, 10)
}

function formatPeriod(period) {
  const formatter = new Intl.DateTimeFormat('zh-CN', { month: 'short', day: 'numeric' })
  return `${formatter.format(new Date(`${period.start_date}T00:00:00`))} - ${formatter.format(new Date(`${period.end_date}T00:00:00`))}`
}

function formatMetric(value, suffix = '', digits = 1) {
  if (value == null) return '未记录'
  const normalized = Number(value)
  return `${Number.isInteger(normalized) ? normalized : normalized.toFixed(digits)}${suffix}`
}

function formatChange(change, suffix = '') {
  if (!change || change.delta == null) return '缺少同期数据'
  if (change.delta === 0) return '与上周持平'
  const sign = change.delta > 0 ? '+' : ''
  return `较上周 ${sign}${Number(change.delta).toFixed(Number.isInteger(change.delta) ? 0 : 1)}${suffix}`
}

async function requestWeeklyAnalytics(userId, anchorDate, signal) {
  const query = new URLSearchParams({
    user_id: String(userId),
    anchor_date: anchorDate,
  })
  const response = await fetch(`${apiBaseUrl}/analytics/weekly?${query.toString()}`, { signal })
  const payload = await response.json()
  if (!response.ok) throw new Error(payload.detail ?? `请求失败: ${response.status}`)
  return payload
}

function TrendTooltip({ active, payload, label, unit = '' }) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-2xl border border-white/70 bg-[rgba(255,255,255,0.94)] px-4 py-3 shadow-[0_16px_42px_rgba(50,67,62,0.14)] backdrop-blur-xl">
      <p className="mb-2 text-xs font-extrabold text-[var(--text)]">{label}</p>
      {payload.map((entry) => (
        <p key={entry.dataKey} className="mt-1 text-xs font-semibold" style={{ color: entry.color }}>
          {entry.name}：{entry.value == null ? '未记录' : `${entry.value}${unit || (
            entry.dataKey.includes('Calories') ? ' kcal'
              : entry.dataKey.includes('Protein') ? 'g'
                : ''
          )}`}
        </p>
      ))}
    </div>
  )
}

function ComparisonCard({ eyebrow, value, change, detail, Icon, tone = 'blue' }) {
  const toneClass = tone === 'mint'
    ? 'bg-[rgba(84,185,156,0.14)] text-[#328970]'
    : tone === 'amber'
      ? 'bg-[rgba(228,168,83,0.14)] text-[#a66d18]'
      : 'bg-[rgba(79,140,255,0.11)] text-[var(--accent)]'

  return (
    <article className="lift-card relative overflow-hidden rounded-[1.55rem] border border-white/70 bg-[rgba(255,255,255,0.72)] p-5 shadow-[0_16px_44px_rgba(94,116,108,0.08)] backdrop-blur-2xl">
      <div className="absolute -right-8 -top-10 h-28 w-28 rounded-full bg-[radial-gradient(circle,rgba(119,199,176,0.14),transparent_68%)]" />
      <div className="relative flex items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-extrabold uppercase tracking-[0.22em] text-[var(--text-faint)]">{eyebrow}</p>
          <p className="mt-3 text-[2rem] font-extrabold leading-none tracking-[-0.055em] text-[var(--text)]">{value}</p>
          <p className="mt-3 text-xs font-bold text-[var(--text-soft)]">{change}</p>
          <p className="mt-1 text-[11px] leading-5 text-[var(--text-faint)]">{detail}</p>
        </div>
        <span className={`inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full ${toneClass}`}>
          <Icon size={19} strokeWidth={2.3} />
        </span>
      </div>
    </article>
  )
}

function ChartPanel({ eyebrow, title, description, children, className = '' }) {
  return (
    <article className={`overflow-hidden rounded-[1.7rem] border border-white/70 bg-[rgba(255,255,255,0.74)] p-5 shadow-[0_18px_54px_rgba(92,113,106,0.08)] backdrop-blur-2xl sm:p-6 ${className}`}>
      <p className="text-[10px] font-extrabold uppercase tracking-[0.25em] text-[var(--text-faint)]">{eyebrow}</p>
      <h2 className="mt-2 text-xl font-extrabold tracking-[-0.035em] text-[var(--text)]">{title}</h2>
      <p className="mt-1 text-xs leading-5 text-[var(--text-soft)]">{description}</p>
      <div className="mt-6 h-64 min-w-0">{children}</div>
    </article>
  )
}

function WeeklySkeleton() {
  return (
    <div className="mt-6 space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {[1, 2, 3, 4].map((item) => <div key={item} className="skeleton-shimmer h-40 rounded-[1.55rem]" />)}
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        {[1, 2, 3, 4].map((item) => <div key={item} className="skeleton-shimmer h-80 rounded-[1.7rem]" />)}
      </div>
    </div>
  )
}

function WeeklyTrends({ session, onBackToChat }) {
  const userId = session.userId ?? 1
  const [anchorDate, setAnchorDate] = useState(() => toInputDate(new Date()))
  const [analytics, setAnalytics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    requestWeeklyAnalytics(userId, anchorDate, controller.signal)
      .then(setAnalytics)
      .catch((requestError) => {
        if (requestError.name !== 'AbortError') {
          setError(requestError instanceof Error ? requestError.message : '周报趋势加载失败')
          setAnalytics(null)
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [anchorDate, userId])

  const selectAnchorDate = (nextDate) => {
    setLoading(true)
    setError('')
    setAnchorDate(nextDate)
  }

  const shiftWeek = (amount) => {
    const next = new Date(`${anchorDate}T00:00:00`)
    next.setDate(next.getDate() + amount)
    const today = new Date()
    selectAnchorDate(toInputDate(next > today ? today : next))
  }

  const dailySeries = analytics?.daily_series.map((point) => ({
    name: point.weekday,
    currentWorkouts: point.current?.workout_records ?? null,
    previousWorkouts: point.previous?.workout_records ?? null,
    currentCalories: point.current?.calories ?? null,
    previousCalories: point.previous?.calories ?? null,
    currentProtein: point.current?.protein_g ?? null,
    previousProtein: point.previous?.protein_g ?? null,
    currentSleep: point.current?.sleep_hours ?? null,
    previousSleep: point.previous?.sleep_hours ?? null,
    currentFatigue: point.current?.fatigue_level ?? null,
    previousFatigue: point.previous?.fatigue_level ?? null,
  })) ?? []

  return (
    <main className="relative min-h-screen overflow-x-hidden bg-[#f5f8f6] text-[var(--text)]">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_12%_0%,rgba(79,140,255,0.14),transparent_27%),radial-gradient(circle_at_88%_2%,rgba(84,185,156,0.16),transparent_24%),linear-gradient(180deg,#fcfdfc_0%,#f2f6f4_100%)]" />
      <div className="soft-grid pointer-events-none fixed inset-x-0 top-0 h-[32rem] opacity-50" />

      <section className="relative mx-auto w-[min(94vw,1320px)] pb-16 pt-6 sm:pt-9">
        <header className="fade-up flex flex-wrap items-start justify-between gap-5">
          <div className="flex items-start gap-4">
            <button
              type="button"
              onClick={onBackToChat}
              className="mt-1 inline-flex h-11 w-11 items-center justify-center rounded-full border border-white/80 bg-white/70 text-[var(--text-soft)] shadow-[0_10px_28px_rgba(91,112,105,0.09)] backdrop-blur-xl transition-all duration-300 hover:-translate-x-0.5 hover:text-[var(--text)]"
              aria-label="返回聊天"
            >
              <ArrowLeft size={19} />
            </button>
            <div>
              <div className="flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-[var(--mint)] shadow-[0_0_0_5px_rgba(119,199,176,0.13)]" />
                <p className="text-[10px] font-extrabold uppercase tracking-[0.3em] text-[var(--text-faint)]">Weekly Field Notes</p>
              </div>
              <h1 className="mt-2 font-display text-[2.7rem] leading-none tracking-[-0.05em] text-[var(--text)] sm:text-[3.7rem]">周报与趋势</h1>
              <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--text-soft)]">把这一周的训练、营养与恢复，折叠成一张可以行动的地图。</p>
            </div>
          </div>

          <div className="flex items-center gap-2 rounded-full border border-white/80 bg-white/70 p-1.5 shadow-[0_12px_34px_rgba(91,112,105,0.08)] backdrop-blur-xl">
            <button type="button" onClick={() => shiftWeek(-7)} className="inline-flex h-9 w-9 items-center justify-center rounded-full text-[var(--text-soft)] transition-colors hover:bg-[rgba(33,52,48,0.05)]" aria-label="上一周"><ChevronLeft size={17} /></button>
            <div className="min-w-36 px-2 text-center">
              <p className="text-[9px] font-extrabold uppercase tracking-[0.2em] text-[var(--text-faint)]">{analytics?.period.is_current_week ? 'Current Week' : 'Archive Week'}</p>
              <p className="mt-0.5 text-xs font-extrabold text-[var(--text)]">{analytics ? formatPeriod(analytics.period.current) : '正在定位周期'}</p>
            </div>
            <button type="button" disabled={analytics?.period.is_current_week} onClick={() => shiftWeek(7)} className="inline-flex h-9 w-9 items-center justify-center rounded-full text-[var(--text-soft)] transition-colors hover:bg-[rgba(33,52,48,0.05)] disabled:cursor-not-allowed disabled:opacity-30" aria-label="下一周"><ChevronRight size={17} /></button>
          </div>
        </header>

        <div className="fade-up-delayed mt-7 flex flex-wrap items-center justify-between gap-3 border-y border-[rgba(33,52,48,0.07)] py-3">
          <div className="flex items-center gap-2 text-xs font-bold text-[var(--text-soft)]">
            <CalendarRange size={15} className="text-[var(--accent)]" />
            {analytics ? `对比 ${formatPeriod(analytics.period.previous)}` : '正在计算同期范围'}
          </div>
          <button type="button" onClick={() => selectAnchorDate(toInputDate(new Date()))} disabled={analytics?.period.is_current_week} className="inline-flex items-center gap-2 rounded-full px-3 py-2 text-xs font-bold text-[var(--accent)] transition-colors hover:bg-[rgba(79,140,255,0.08)] disabled:opacity-40">
            <RefreshCw size={14} />
            回到本周
          </button>
        </div>

        {loading ? <WeeklySkeleton /> : null}
        {!loading && error ? (
          <div className="mt-6 rounded-[1.6rem] border border-[rgba(215,99,99,0.17)] bg-[rgba(255,250,250,0.82)] p-7 text-sm leading-7 text-[var(--danger)] shadow-[0_16px_44px_rgba(130,78,78,0.06)]">
            <p className="font-extrabold">周报趋势暂时无法读取</p>
            <p className="mt-1">{error}</p>
          </div>
        ) : null}

        {!loading && !error && analytics ? (
          <div className="fade-up mt-6">
            <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <ComparisonCard eyebrow="训练频率" value={`${analytics.training.current.record_count} 次`} change={formatChange(analytics.training.changes.record_count, ' 次')} detail={`覆盖 ${analytics.training.current.training_day_count} 个训练日`} Icon={Dumbbell} />
              <ComparisonCard eyebrow="日均蛋白" value={formatMetric(analytics.nutrition.current.average_protein_g, 'g')} change={formatChange(analytics.nutrition.changes.average_protein_g, 'g')} detail={`${analytics.coverage.current.nutrition_days}/${analytics.period.current.day_count} 天有饮食记录`} Icon={Utensils} tone="mint" />
              <ComparisonCard eyebrow="平均睡眠" value={formatMetric(analytics.recovery.current.average_sleep_hours, 'h')} change={formatChange(analytics.recovery.changes.average_sleep_hours, 'h')} detail={`${analytics.coverage.current.body_status_days}/${analytics.period.current.day_count} 天有状态记录`} Icon={MoonStar} tone="blue" />
              <ComparisonCard eyebrow="训练时长" value={formatMetric(analytics.training.current.total_duration_minutes, 'min', 0)} change={formatChange(analytics.training.changes.total_duration_minutes, 'min')} detail="只统计明确填写的训练时长" Icon={Flame} tone="amber" />
            </section>

            <section className="mt-4 grid gap-4 xl:grid-cols-2">
              <ChartPanel eyebrow="Training Rhythm" title="训练节奏" description="每天训练次数，本周与上周同星期位置对齐。">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={dailySeries} barGap={6}>
                    <CartesianGrid vertical={false} stroke="rgba(33,52,48,0.07)" />
                    <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#81908c', fontSize: 11, fontWeight: 700 }} />
                    <YAxis allowDecimals={false} axisLine={false} tickLine={false} width={28} tick={{ fill: '#9aa6a3', fontSize: 10 }} />
                    <Tooltip content={<TrendTooltip />} cursor={{ fill: 'rgba(79,140,255,0.04)' }} />
                    <Legend iconType="circle" wrapperStyle={{ fontSize: 11, fontWeight: 700 }} />
                    <Bar dataKey="previousWorkouts" name="上周" fill={chartColors.previous} radius={[8, 8, 2, 2]} maxBarSize={22} />
                    <Bar dataKey="currentWorkouts" name="本周" fill={chartColors.current} radius={[8, 8, 2, 2]} maxBarSize={22} />
                  </BarChart>
                </ResponsiveContainer>
              </ChartPanel>

              <ChartPanel eyebrow="Nutrition Signal" title="能量与蛋白" description="仅展示有饮食记录日期，空白不是零摄入。">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={dailySeries}>
                    <defs>
                      <linearGradient id="calorieFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor={chartColors.amber} stopOpacity={0.25} />
                        <stop offset="100%" stopColor={chartColors.amber} stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid vertical={false} stroke="rgba(33,52,48,0.07)" />
                    <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#81908c', fontSize: 11, fontWeight: 700 }} />
                    <YAxis yAxisId="calories" axisLine={false} tickLine={false} width={38} tick={{ fill: '#9aa6a3', fontSize: 10 }} />
                    <YAxis yAxisId="protein" orientation="right" axisLine={false} tickLine={false} width={28} tick={{ fill: '#9aa6a3', fontSize: 10 }} />
                    <Tooltip content={<TrendTooltip />} />
                    <Legend iconType="circle" wrapperStyle={{ fontSize: 11, fontWeight: 700 }} />
                    <Area yAxisId="calories" type="monotone" dataKey="previousCalories" name="上周热量" stroke={chartColors.previous} fill="transparent" strokeDasharray="5 5" connectNulls />
                    <Area yAxisId="calories" type="monotone" dataKey="currentCalories" name="本周热量" stroke={chartColors.amber} strokeWidth={2.4} fill="url(#calorieFill)" connectNulls />
                    <Line yAxisId="protein" type="monotone" dataKey="previousProtein" name="上周蛋白" stroke="#a8d8ca" strokeDasharray="4 4" dot={false} connectNulls />
                    <Line yAxisId="protein" type="monotone" dataKey="currentProtein" name="本周蛋白" stroke={chartColors.mint} strokeWidth={2.2} dot={{ r: 2.5 }} connectNulls />
                  </ComposedChart>
                </ResponsiveContainer>
              </ChartPanel>

              <ChartPanel eyebrow="Recovery Curve" title="睡眠恢复" description="睡眠时长按日呈现，帮助识别恢复节奏。">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={dailySeries}>
                    <CartesianGrid vertical={false} stroke="rgba(33,52,48,0.07)" />
                    <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#81908c', fontSize: 11, fontWeight: 700 }} />
                    <YAxis domain={[0, 10]} axisLine={false} tickLine={false} width={28} tick={{ fill: '#9aa6a3', fontSize: 10 }} />
                    <Tooltip content={<TrendTooltip unit="h" />} />
                    <Legend iconType="circle" wrapperStyle={{ fontSize: 11, fontWeight: 700 }} />
                    <Line type="monotone" dataKey="previousSleep" name="上周睡眠" stroke={chartColors.previous} strokeWidth={2} strokeDasharray="5 5" dot={false} connectNulls />
                    <Line type="monotone" dataKey="currentSleep" name="本周睡眠" stroke={chartColors.mint} strokeWidth={2.6} dot={{ r: 3, fill: '#fff', strokeWidth: 2 }} connectNulls />
                  </LineChart>
                </ResponsiveContainer>
              </ChartPanel>

              <ChartPanel eyebrow="Training Map" title="部位分布" description="按动作映射统计；复合动作可能同时计入多个部位。">
                {analytics.muscle_distribution.length ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={analytics.muscle_distribution} layout="vertical" margin={{ left: 4 }}>
                      <CartesianGrid horizontal={false} stroke="rgba(33,52,48,0.07)" />
                      <XAxis type="number" allowDecimals={false} axisLine={false} tickLine={false} tick={{ fill: '#9aa6a3', fontSize: 10 }} />
                      <YAxis type="category" dataKey="label" axisLine={false} tickLine={false} width={42} tick={{ fill: '#667672', fontSize: 11, fontWeight: 700 }} />
                      <Tooltip content={<TrendTooltip unit=" 项" />} cursor={{ fill: 'rgba(84,185,156,0.04)' }} />
                      <Legend iconType="circle" wrapperStyle={{ fontSize: 11, fontWeight: 700 }} />
                      <Bar dataKey="previous_count" name="上周" fill={chartColors.previous} radius={[0, 8, 8, 0]} maxBarSize={13} />
                      <Bar dataKey="current_count" name="本周" fill={chartColors.mint} radius={[0, 8, 8, 0]} maxBarSize={13} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex h-full flex-col items-center justify-center text-center">
                    <Activity size={26} className="text-[var(--text-faint)]" />
                    <p className="mt-3 text-sm font-bold text-[var(--text)]">还没有可映射的动作记录</p>
                    <p className="mt-1 text-xs text-[var(--text-faint)]">记录具体动作后，这里会形成你的训练版图。</p>
                  </div>
                )}
              </ChartPanel>
            </section>

            <aside className="mt-4 flex flex-wrap items-center justify-between gap-4 rounded-[1.55rem] border border-[rgba(79,140,255,0.09)] bg-[linear-gradient(120deg,rgba(79,140,255,0.08),rgba(84,185,156,0.1))] px-5 py-4">
              <div className="flex items-center gap-3">
                <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-white/75 text-[var(--accent)]"><Sparkles size={17} /></span>
                <div>
                  <p className="text-sm font-extrabold text-[var(--text)]">周报只计算已记录事实</p>
                  <p className="mt-0.5 text-xs leading-5 text-[var(--text-soft)]">想获得自然语言解读，可以回到聊天输入“生成我的本周周报”。</p>
                </div>
              </div>
              <button type="button" onClick={onBackToChat} className="rounded-full bg-white/80 px-4 py-2.5 text-xs font-extrabold text-[var(--accent)] shadow-[0_8px_20px_rgba(79,140,255,0.08)] transition-transform hover:-translate-y-0.5">去聊天生成周报</button>
            </aside>
          </div>
        ) : null}
      </section>
    </main>
  )
}

export default WeeklyTrends
