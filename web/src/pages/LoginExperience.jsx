import { useEffect, useState } from 'react'

const athleteImage =
  'https://images.pexels.com/photos/31028213/pexels-photo-31028213.jpeg?cs=srgb&dl=pexels-modelstma-31028213.jpg&fm=jpg'

const gymMoodImage =
  'https://images.pexels.com/photos/9669473/pexels-photo-9669473.jpeg?cs=srgb&dl=pexels-matreding-9669473.jpg&fm=jpg'

const quickSignals = [
  ['训练', '计划与完成同轨'],
  ['恢复', '睡眠与疲劳留痕'],
  ['饮食', '摄入与补剂入档'],
]

const defaultCredentials = {
  identifiers: ['fitmind', 'demo', 'demo@fitmind.ai'],
  password: '123456',
}

function LoginExperience({ onLoginSuccess }) {
  const [launching, setLaunching] = useState(false)
  const [started, setStarted] = useState(false)
  const [mode, setMode] = useState('login')
  const [loginForm, setLoginForm] = useState({
    identifier: 'fitmind',
    password: '123456',
  })
  const [registerForm, setRegisterForm] = useState({
    email: '',
    username: '',
    password: '',
  })
  const [loginErrors, setLoginErrors] = useState({})
  const [registerErrors, setRegisterErrors] = useState({})
  const [loginStatus, setLoginStatus] = useState({
    type: '',
    message: '',
  })
  const [registerStatus, setRegisterStatus] = useState({
    type: '',
    message: '',
  })
  const [submitting, setSubmitting] = useState({
    login: false,
    register: false,
  })

  const isLogin = mode === 'login'
  const activeIndex = isLogin ? 'translate-x-0' : 'translate-x-full'

  useEffect(() => {
    if (!launching) {
      return undefined
    }

    const timer = window.setTimeout(() => {
      setLaunching(false)
    }, 1100)

    return () => window.clearTimeout(timer)
  }, [launching])

  const handleStart = () => {
    setStarted(true)
    setLaunching(true)
  }

  const handleReset = () => {
    setStarted(false)
    setLaunching(false)
  }

  const handleModeChange = (nextMode) => {
    setMode(nextMode)
    if (nextMode === 'login') {
      setRegisterStatus({ type: '', message: '' })
    } else {
      setLoginStatus({ type: '', message: '' })
    }
  }

  const handleLoginInput = (event) => {
    const { name, value } = event.target

    setLoginForm((current) => ({
      ...current,
      [name]: value,
    }))

    setLoginErrors((current) => ({
      ...current,
      [name]: '',
    }))
  }

  const handleRegisterInput = (event) => {
    const { name, value } = event.target

    setRegisterForm((current) => ({
      ...current,
      [name]: value,
    }))

    setRegisterErrors((current) => ({
      ...current,
      [name]: '',
    }))
  }

  const validateLogin = (values) => {
    const errors = {}

    if (!values.identifier.trim()) {
      errors.identifier = '请输入账号'
    }

    if (!values.password) {
      errors.password = '请输入密码'
    } else if (values.password.length < 6) {
      errors.password = '密码至少 6 位'
    }

    return errors
  }

  const validateRegister = (values) => {
    const errors = {}
    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    const usernamePattern = /^[a-zA-Z0-9_\u4e00-\u9fa5]{3,20}$/

    if (!values.email.trim()) {
      errors.email = '请输入邮箱'
    } else if (!emailPattern.test(values.email)) {
      errors.email = '邮箱格式错误'
    }

    if (!values.username.trim()) {
      errors.username = '请输入用户名'
    } else if (!usernamePattern.test(values.username)) {
      errors.username = '用户名需 3-20 位'
    }

    if (!values.password) {
      errors.password = '请输入密码'
    } else if (values.password.length < 6) {
      errors.password = '密码至少 6 位'
    }

    return errors
  }

  const fakeLoginApi = async (payload) => {
    await new Promise((resolve) => window.setTimeout(resolve, 650))

    const normalizedIdentifier = payload.identifier.trim().toLowerCase()
    const isAllowedUser = defaultCredentials.identifiers.includes(normalizedIdentifier)

    if (!isAllowedUser || payload.password !== defaultCredentials.password) {
      return {
        ok: false,
        message: '默认账号: fitmind / 默认密码: 123456',
      }
    }

    return {
      ok: true,
      message: '登录成功，正在进入对话页...',
      user: {
        name: normalizedIdentifier === 'demo@fitmind.ai' ? 'FitMind Demo' : 'FitMind',
        identifier: payload.identifier,
      },
    }
  }

  const fakeRegisterApi = async (payload) => {
    await new Promise((resolve) => window.setTimeout(resolve, 900))

    if (payload.email.toLowerCase().endsWith('@example.com')) {
      return {
        ok: false,
        message: '请使用真实邮箱',
      }
    }

    if (payload.username.toLowerCase() === 'admin') {
      return {
        ok: false,
        message: '用户名已被占用',
      }
    }

    return {
      ok: true,
      message: '注册成功，请使用默认账号体验',
    }
  }

  const handleLoginSubmit = async (event) => {
    event.preventDefault()

    const errors = validateLogin(loginForm)
    setLoginErrors(errors)
    setLoginStatus({ type: '', message: '' })

    if (Object.keys(errors).length > 0) {
      return
    }

    setSubmitting((current) => ({ ...current, login: true }))

    const response = await fakeLoginApi(loginForm)

    setSubmitting((current) => ({ ...current, login: false }))
    setLoginStatus({
      type: response.ok ? 'success' : 'error',
      message: response.message,
    })

    if (response.ok) {
      window.setTimeout(() => {
        onLoginSuccess(response.user)
      }, 420)
    }
  }

  const handleRegisterSubmit = async (event) => {
    event.preventDefault()

    const errors = validateRegister(registerForm)
    setRegisterErrors(errors)
    setRegisterStatus({ type: '', message: '' })

    if (Object.keys(errors).length > 0) {
      return
    }

    setSubmitting((current) => ({ ...current, register: true }))

    const response = await fakeRegisterApi(registerForm)

    setSubmitting((current) => ({ ...current, register: false }))
    setRegisterStatus({
      type: response.ok ? 'success' : 'error',
      message: response.message,
    })

    if (response.ok) {
      setMode('login')
    }
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-[var(--shell-bg)] text-[var(--ink-dark)]">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_14%_16%,rgba(141,213,186,0.2),transparent_23%),radial-gradient(circle_at_26%_82%,rgba(210,167,105,0.14),transparent_18%),radial-gradient(circle_at_86%_14%,rgba(199,236,226,0.12),transparent_18%),linear-gradient(135deg,#07100f_0%,#0b1715_42%,#101715_100%)]" />
      <div className="grid-noise absolute inset-0 opacity-40" />
      <div className="absolute -left-20 top-24 h-72 w-72 rounded-full bg-emerald-200/10 blur-3xl" />
      <div className="absolute bottom-0 right-12 h-80 w-80 rounded-full bg-amber-200/10 blur-3xl" />

      <div className="relative mx-auto min-h-screen max-w-[1600px] px-4 py-4 sm:px-6 lg:px-8">
        <section className="relative isolate min-h-[calc(100svh-2rem)] overflow-hidden rounded-[2rem] border border-white/10 bg-[rgba(255,248,241,0.03)] shadow-[0_30px_120px_rgba(4,12,10,0.58)] backdrop-blur-sm">
          <div className="pointer-events-none absolute inset-0">
            <div className="absolute right-[8%] top-[10%] hidden h-[68%] w-[34rem] overflow-hidden rounded-[2rem] border border-white/10 shadow-[0_30px_90px_rgba(0,0,0,0.4)] lg:block">
              <img
                src={athleteImage}
                alt="夜间训练中的健身场景"
                className="h-full w-full object-cover object-center opacity-52 saturate-[0.58] sepia-[0.12]"
              />
              <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(8,16,14,0.92),rgba(8,16,14,0.45)_45%,rgba(8,16,14,0.7))]" />
            </div>

            <div className="absolute bottom-[9%] right-[18%] hidden h-[30%] w-[16rem] overflow-hidden rounded-[2rem] border border-white/10 shadow-[0_20px_70px_rgba(0,0,0,0.38)] lg:block">
              <img
                src={gymMoodImage}
                alt="深色拳击训练空间"
                className="h-full w-full object-cover object-center opacity-68 grayscale-[0.18] sepia-[0.18]"
              />
              <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(8,16,14,0.18),rgba(8,16,14,0.72))]" />
            </div>
          </div>

          <div className="relative min-h-[calc(100svh-2rem)]">
            <section
              className={`relative flex min-h-[calc(100svh-2rem)] flex-col justify-between overflow-hidden px-6 py-6 transition-[width,transform,padding] duration-[1100ms] ease-[cubic-bezier(0.22,1,0.36,1)] sm:px-8 sm:py-8 lg:px-12 lg:py-10 ${
                started
                  ? `lg:w-[56%] ${launching ? 'scale-[0.985] translate-x-[-1%]' : 'scale-100'}`
                  : 'w-full'
              }`}
            >
              <div className="hero-veil absolute inset-0" />
              <div className="pointer-events-none absolute inset-y-0 right-0 hidden w-[42%] bg-[linear-gradient(90deg,rgba(8,16,14,0),rgba(8,16,14,0.14),rgba(8,16,14,0.92))] lg:block" />
              <div
                className={`storyboard-flash pointer-events-none absolute inset-0 transition-opacity duration-700 ${
                  launching ? 'opacity-100' : 'opacity-0'
                }`}
              />
              <div className="pointer-events-none absolute left-8 top-8 h-16 w-16 rounded-full border border-white/10 bg-white/[0.03] blur-[1px]" />
              <div className="pointer-events-none absolute bottom-14 left-[38%] h-px w-32 bg-gradient-to-r from-transparent via-emerald-100/45 to-transparent" />
              <div className="pointer-events-none absolute left-[14%] top-[24%] hidden h-44 w-44 rounded-full border border-white/6 lg:block" />

              <header className="relative z-10 flex items-center justify-between">
                <div className="animate-rise">
                  <p className="font-mono text-[0.68rem] uppercase tracking-[0.4em] text-emerald-50/70">
                    FitMind
                  </p>
                  <p className="mt-2 text-sm text-stone-200/76">
                    健身健康智能体
                  </p>
                </div>
                <div className="animate-rise-delayed hidden rounded-full border border-emerald-100/10 bg-white/6 px-4 py-2 font-mono text-[0.65rem] uppercase tracking-[0.28em] text-stone-100/70 backdrop-blur sm:block">
                  Memory Flow
                </div>
              </header>

              <div className="relative z-30 grid flex-1 items-center gap-10 py-10 lg:grid-cols-[minmax(0,1fr)_14rem] lg:gap-12 lg:py-0">
                <div className="max-w-[44rem]">
                  <div className="animate-rise inline-flex items-center gap-3 rounded-full border border-emerald-100/12 bg-white/6 px-4 py-2 font-mono text-[0.68rem] uppercase tracking-[0.28em] text-stone-100/72 backdrop-blur">
                    <span className="h-2 w-2 rounded-full bg-[var(--accent-jade)] shadow-[0_0_18px_var(--accent-jade)]" />
                    运动记忆引擎
                  </div>

                  <h1
                    className={`animate-rise-delayed mt-8 max-w-5xl font-display font-semibold leading-[0.9] tracking-[-0.045em] text-[var(--ink-dark)] transition-all duration-[1100ms] ease-[cubic-bezier(0.22,1,0.36,1)] ${
                      started ? 'text-[2.6rem] sm:text-[3.6rem] lg:text-[4.3rem]' : 'text-[3.4rem] sm:text-[5.4rem] lg:text-[6.5rem]'
                    }`}
                  >
                    训练有迹。
                    <span className="block text-[var(--accent-mist)]">健康有章。</span>
                  </h1>

                  <p
                    className={`animate-rise-soft mt-6 max-w-xl text-stone-200/82 transition-all duration-[1100ms] ease-[cubic-bezier(0.22,1,0.36,1)] ${
                      started ? 'text-sm leading-7 sm:text-[0.96rem]' : 'text-base leading-7 sm:text-[1.02rem]'
                    }`}
                  >
                    用对话记录训练、恢复与饮食。
                  </p>

                  <div className="animate-rise-soft mt-10 flex flex-wrap gap-4">
                    <button
                      type="button"
                      onClick={handleStart}
                      className="shine-button"
                    >
                      即刻开始
                    </button>
                    {started && (
                      <button
                        type="button"
                        onClick={handleReset}
                        className="glass-button"
                      >
                        返回首页
                      </button>
                    )}
                  </div>
                </div>

                <div className="hidden self-stretch lg:flex">
                  <div className="animate-card flex w-full flex-col justify-between rounded-[1.7rem] border border-white/10 bg-[linear-gradient(180deg,rgba(255,248,241,0.09),rgba(255,248,241,0.02))] p-5 backdrop-blur">
                    <div>
                      <p className="font-mono text-[0.62rem] uppercase tracking-[0.3em] text-stone-200/56">
                        Today
                      </p>
                      <div className="mt-6 space-y-3 text-right">
                        <p className="font-display text-5xl font-semibold tracking-[-0.06em] text-[var(--ink-dark)]">
                          24
                        </p>
                        <p className="text-sm leading-6 text-stone-200/76">
                          对话沉淀为记录
                        </p>
                      </div>
                    </div>
                    <div className="border-t border-white/10 pt-4">
                      <p className="font-mono text-[0.6rem] uppercase tracking-[0.26em] text-stone-300/60">
                        memory trace
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <footer className="relative z-10 mt-8 border-t border-white/10 pt-5">
                <div className="grid max-w-4xl gap-3 sm:grid-cols-3">
                  {quickSignals.map(([label, value], index) => (
                    <div
                      key={label}
                      className="signal-card animate-card rounded-[1.55rem] border border-white/10 bg-white/[0.04] px-4 py-4 backdrop-blur"
                      style={{ animationDelay: `${0.2 + index * 0.08}s` }}
                    >
                      <p className="font-mono text-[0.62rem] uppercase tracking-[0.28em] text-stone-200/45">
                        {label}
                      </p>
                      <p className="mt-2 text-sm leading-6 text-stone-100/88">
                        {value}
                      </p>
                    </div>
                  ))}
                </div>
              </footer>
            </section>

            <section className="auth-stage absolute inset-y-0 right-0 z-40 flex w-full items-center justify-end px-4 py-5 sm:px-6 sm:py-6 lg:w-[44%] lg:px-9 lg:py-8">
              <div
                className={`auth-shell my-auto w-full max-w-[31.5rem] rounded-[1.85rem] border border-[#efe5d7]/70 bg-[linear-gradient(180deg,rgba(255,250,242,0.985),rgba(239,229,215,0.95))] p-4 shadow-[0_30px_100px_rgba(12,18,15,0.34)] backdrop-blur transition-all duration-[1100ms] ease-[cubic-bezier(0.22,1,0.36,1)] md:p-5 ${
                  started
                    ? 'pointer-events-auto translate-x-0 opacity-100 blur-0'
                    : 'pointer-events-none translate-x-[108%] opacity-0 blur-md'
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="font-mono text-[0.62rem] uppercase tracking-[0.26em] text-[#7d6652]">
                      FitMind Access
                    </p>
                    <h2 className="mt-2 font-display text-[1.85rem] font-semibold leading-none tracking-[-0.03em] text-[#1f221d] md:text-[2.2rem]">
                      {isLogin ? '欢迎回来' : '创建账号'}
                    </h2>
                    <p className="mt-2 max-w-md text-[0.92rem] leading-6 text-[#645646]">
                      {isLogin ? '使用默认账号直接进入。' : '体验版默认开放登录。'}
                    </p>
                  </div>
                  <div className="hidden rounded-full border border-[#d8c8b6] bg-white/65 px-3 py-2 font-mono text-[0.6rem] uppercase tracking-[0.24em] text-[#7d6652] sm:block">
                    Curated
                  </div>
                </div>

                <div className="relative z-30 mt-5 grid grid-cols-2 rounded-[1.05rem] border border-[#d8c8b6] bg-[#f2eadf] p-1 shadow-[inset_0_1px_0_rgba(255,255,255,0.88)]">
                  <span
                    aria-hidden="true"
                    className={`auth-switch-indicator ${activeIndex}`}
                  />
                  <button
                    type="button"
                    onClick={() => handleModeChange('login')}
                    className={`relative z-10 rounded-[0.95rem] px-4 py-2.5 font-mono text-[0.68rem] uppercase tracking-[0.22em] transition-all duration-500 ${
                      isLogin
                        ? 'text-white'
                        : 'text-[#7f6a57] hover:text-[#1f221d]'
                    }`}
                  >
                    登录
                  </button>
                  <button
                    type="button"
                    onClick={() => handleModeChange('register')}
                    className={`relative z-10 rounded-[0.95rem] px-4 py-2.5 font-mono text-[0.68rem] uppercase tracking-[0.22em] transition-all duration-500 ${
                      !isLogin
                        ? 'text-white'
                        : 'text-[#7f6a57] hover:text-[#1f221d]'
                    }`}
                  >
                    注册
                  </button>
                </div>

                <div className={`relative z-20 mt-4 ${isLogin ? 'min-h-[18rem]' : 'min-h-[16.5rem]'}`}>
                  {isLogin ? (
                    <form
                      key="login-form"
                      className="auth-form-panel auth-form-panel-active"
                      autoComplete="on"
                      onSubmit={handleLoginSubmit}
                    >
                      <div className="space-y-3">
                        <label className="block">
                          <span className="mb-2 block font-mono text-[0.68rem] uppercase tracking-[0.24em] text-[#7d6652]">
                            邮箱或用户名
                          </span>
                          <input
                            type="text"
                            name="identifier"
                            placeholder="输入 fitmind 或 demo@fitmind.ai"
                            value={loginForm.identifier}
                            onChange={handleLoginInput}
                            className="w-full rounded-[1.2rem] border border-[#dbcfc0] bg-white/88 px-4 py-3.5 text-[15px] text-[#231f19] outline-none transition duration-300 placeholder:text-[#a08d78] focus:border-[#8dd5ba] focus:ring-4 focus:ring-[#dcefe7]"
                          />
                          <p className="mt-1.5 min-h-4 text-[0.82rem] text-rose-500">{loginErrors.identifier || ' '}</p>
                        </label>
                        <label className="block">
                          <span className="mb-2 block font-mono text-[0.68rem] uppercase tracking-[0.24em] text-[#7d6652]">
                            密码
                          </span>
                          <input
                            type="password"
                            name="password"
                            placeholder="输入默认密码 123456"
                            value={loginForm.password}
                            onChange={handleLoginInput}
                            className="w-full rounded-[1.2rem] border border-[#dbcfc0] bg-white/88 px-4 py-3.5 text-[15px] text-[#231f19] outline-none transition duration-300 placeholder:text-[#a08d78] focus:border-[#8dd5ba] focus:ring-4 focus:ring-[#dcefe7]"
                          />
                          <p className="mt-1.5 min-h-4 text-[0.82rem] text-rose-500">{loginErrors.password || ' '}</p>
                        </label>
                      </div>

                      <div className="mt-3.5 rounded-[1.1rem] border border-[#e6d8c8] bg-white/65 px-4 py-3 text-[0.88rem] leading-6 text-[#6d5b49]">
                        默认账号: <span className="font-mono text-[#1f221d]">fitmind</span>
                        <span className="mx-2 text-[#b9a792]">/</span>
                        默认密码: <span className="font-mono text-[#1f221d]">123456</span>
                      </div>

                      <div className="mt-3.5 min-h-[3rem]">
                        {loginStatus.message && (
                          <p
                            className={`rounded-[1rem] px-3 py-2 text-[0.82rem] leading-5 ${
                              loginStatus.type === 'success'
                                ? 'bg-emerald-50 text-emerald-700'
                                : 'bg-rose-50 text-rose-600'
                            }`}
                          >
                            {loginStatus.message}
                          </p>
                        )}
                      </div>

                      <button
                        type="submit"
                        disabled={submitting.login}
                        className="shine-button mt-3 w-full justify-center disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {submitting.login ? '登录中...' : '进入对话页'}
                      </button>
                    </form>
                  ) : (
                    <form
                      key="register-form"
                      className="auth-form-panel auth-form-panel-active"
                      autoComplete="on"
                      onSubmit={handleRegisterSubmit}
                    >
                      <div className="space-y-3">
                        <label className="block">
                          <span className="mb-2 block font-mono text-[0.68rem] uppercase tracking-[0.24em] text-[#7d6652]">
                            邮箱
                          </span>
                          <input
                            type="email"
                            name="email"
                            placeholder="输入邮箱"
                            value={registerForm.email}
                            onChange={handleRegisterInput}
                            className="w-full rounded-[1.2rem] border border-[#dbcfc0] bg-white/88 px-4 py-3.5 text-[15px] text-[#231f19] outline-none transition duration-300 placeholder:text-[#a08d78] focus:border-[#8dd5ba] focus:ring-4 focus:ring-[#dcefe7]"
                          />
                          <p className="mt-1.5 min-h-4 text-[0.82rem] text-rose-500">{registerErrors.email || ' '}</p>
                        </label>
                        <label className="block">
                          <span className="mb-2 block font-mono text-[0.68rem] uppercase tracking-[0.24em] text-[#7d6652]">
                            用户名
                          </span>
                          <input
                            type="text"
                            name="username"
                            placeholder="输入用户名"
                            value={registerForm.username}
                            onChange={handleRegisterInput}
                            className="w-full rounded-[1.2rem] border border-[#dbcfc0] bg-white/88 px-4 py-3.5 text-[15px] text-[#231f19] outline-none transition duration-300 placeholder:text-[#a08d78] focus:border-[#8dd5ba] focus:ring-4 focus:ring-[#dcefe7]"
                          />
                          <p className="mt-1.5 min-h-4 text-[0.82rem] text-rose-500">{registerErrors.username || ' '}</p>
                        </label>
                        <label className="block">
                          <span className="mb-2 block font-mono text-[0.68rem] uppercase tracking-[0.24em] text-[#7d6652]">
                            密码
                          </span>
                          <input
                            type="password"
                            name="password"
                            placeholder="设置密码"
                            value={registerForm.password}
                            onChange={handleRegisterInput}
                            className="w-full rounded-[1.2rem] border border-[#dbcfc0] bg-white/88 px-4 py-3.5 text-[15px] text-[#231f19] outline-none transition duration-300 placeholder:text-[#a08d78] focus:border-[#8dd5ba] focus:ring-4 focus:ring-[#dcefe7]"
                          />
                          <p className="mt-1.5 min-h-4 text-[0.82rem] text-rose-500">{registerErrors.password || ' '}</p>
                        </label>
                      </div>

                      <div className="mt-2 min-h-[2.25rem]">
                        {registerStatus.message && (
                          <p
                            className={`rounded-[1rem] px-3 py-2 text-[0.82rem] leading-5 ${
                              registerStatus.type === 'success'
                                ? 'bg-emerald-50 text-emerald-700'
                                : 'bg-rose-50 text-rose-600'
                            }`}
                          >
                            {registerStatus.message}
                          </p>
                        )}
                      </div>

                      <button
                        type="submit"
                        disabled={submitting.register}
                        className="shine-button mt-3 w-full justify-center disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {submitting.register ? '创建中...' : '创建账号'}
                      </button>
                    </form>
                  )}
                </div>

                <p className="mt-3.5 text-center text-[0.9rem] text-[#7f6a57]">
                  {isLogin ? '还没有账号？' : '已经有账号？'}
                  <button
                    type="button"
                    onClick={() => handleModeChange(isLogin ? 'register' : 'login')}
                    className="ml-2 font-medium text-[#1f221d] transition-colors duration-300 hover:text-[#486c5c]"
                  >
                    {isLogin ? '立即注册' : '去登录'}
                  </button>
                </p>
              </div>
            </section>
          </div>
        </section>
      </div>
    </main>
  )
}

export default LoginExperience
