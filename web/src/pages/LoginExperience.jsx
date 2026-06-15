import { useState } from 'react'

const quickNotes = [
  { label: '训练', value: '对话即记录，减少切换成本' },
  { label: '饮食', value: '补一条早餐或补剂只要一句话' },
  { label: '恢复', value: '睡眠、疲劳、体重统一进入记忆' },
]

const defaultCredentials = {
  identifiers: ['fitmind', 'demo', 'demo@fitmind.ai'],
  password: '123456',
}

const fieldBaseClass =
  'w-full rounded-[1.15rem] border border-[var(--line)] bg-white px-4 py-3.5 text-[15px] text-[var(--text)] outline-none transition-all duration-300 placeholder:text-[var(--text-faint)] focus:border-[rgba(79,140,255,0.38)] focus:ring-4 focus:ring-[rgba(79,140,255,0.12)]'

function LoginExperience({ onLoginSuccess }) {
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
  const [loginStatus, setLoginStatus] = useState({ type: '', message: '' })
  const [registerStatus, setRegisterStatus] = useState({ type: '', message: '' })
  const [submitting, setSubmitting] = useState({ login: false, register: false })

  const isLogin = mode === 'login'

  const handleLoginInput = (event) => {
    const { name, value } = event.target
    setLoginForm((current) => ({ ...current, [name]: value }))
    setLoginErrors((current) => ({ ...current, [name]: '' }))
  }

  const handleRegisterInput = (event) => {
    const { name, value } = event.target
    setRegisterForm((current) => ({ ...current, [name]: value }))
    setRegisterErrors((current) => ({ ...current, [name]: '' }))
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
      message: '登录成功，正在进入工作台...',
      user: {
        userId: 1,
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
      message: '注册成功，请直接使用默认账号体验',
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
      }, 320)
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
    <main className="relative min-h-screen overflow-hidden px-4 py-4 sm:px-6 sm:py-6">
      <div className="soft-grid pointer-events-none absolute inset-0 opacity-70" />
      <div className="hero-orb left-[-4rem] top-[10%] h-52 w-52 bg-[rgba(119,199,176,0.2)]" />
      <div className="hero-orb right-[5%] top-[8%] h-56 w-56 bg-[rgba(79,140,255,0.14)]" />
      <div className="hero-orb bottom-[8%] left-[12%] h-44 w-44 bg-[rgba(255,214,179,0.2)]" />

      <section className="relative mx-auto grid min-h-[calc(100svh-2rem)] max-w-[1440px] overflow-hidden rounded-[2rem] border border-white/70 bg-[rgba(255,255,255,0.56)] shadow-[var(--shadow-lg)] backdrop-blur xl:grid-cols-[1.1fr_0.9fr]">
        <div className="relative flex flex-col justify-between overflow-hidden px-6 py-8 sm:px-9 lg:px-12 lg:py-12">
          <div className="fade-up">
            <div className="inline-flex items-center gap-3 rounded-full border border-white/80 bg-white/72 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.28em] text-[var(--text-soft)]">
              <span className="h-2 w-2 rounded-full bg-[var(--mint)]" />
              FitMind
            </div>
            <h1 className="mt-8 max-w-[10ch] font-display text-[3.4rem] leading-[0.9] tracking-[-0.045em] text-[var(--text)] sm:text-[4.4rem] lg:text-[5.6rem]">
              把训练日常，
              <span className="text-[var(--accent)]">说给 AI 听。</span>
            </h1>
            <p className="mt-6 max-w-xl text-[15px] leading-8 text-[var(--text-soft)] sm:text-[17px]">
              一个以对话为核心的健身数据记录助手。你只需要输入训练、饮食、睡眠或体重，它会替你整理、记忆并延续上下文。
            </p>
          </div>

          <div className="fade-up-delayed mt-10 grid gap-4 sm:grid-cols-3 xl:max-w-3xl">
            {quickNotes.map((item) => (
              <article
                key={item.label}
                className="lift-card rounded-[1.5rem] border border-white/75 bg-[rgba(255,255,255,0.66)] p-4 subtle-ring"
              >
                <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-[var(--text-faint)]">
                  {item.label}
                </p>
                <p className="mt-3 text-sm leading-6 text-[var(--text-soft)]">{item.value}</p>
              </article>
            ))}
          </div>

          <div className="mt-10 hidden rounded-[1.8rem] border border-white/75 bg-[linear-gradient(135deg,rgba(79,140,255,0.08),rgba(119,199,176,0.06),rgba(255,255,255,0.68))] p-6 backdrop-blur lg:block">
            <div className="grid grid-cols-[1fr_auto] gap-6">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-[var(--text-faint)]">
                  Daily Focus
                </p>
                <p className="mt-4 max-w-md text-base leading-7 text-[var(--text)]">
                  记录从“表单填写”变成“自然聊天”，这是整个产品最该被记住的一点。
                </p>
              </div>
              <div className="flex items-center rounded-[1.4rem] bg-white/70 px-5 py-4 text-right subtle-ring">
                <div>
                  <p className="font-display text-5xl leading-none tracking-[-0.06em] text-[var(--text)]">
                    24h
                  </p>
                  <p className="mt-2 text-xs uppercase tracking-[0.22em] text-[var(--text-faint)]">
                    Memory Flow
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-center bg-[linear-gradient(180deg,rgba(251,252,251,0.72),rgba(244,247,246,0.92))] px-4 py-6 sm:px-6 lg:px-10">
          <div className="glass-panel w-full max-w-[30rem] rounded-[2rem] border border-white/85 p-5 shadow-[var(--shadow-lg)] sm:p-7">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-[var(--text-faint)]">
                  Secure Access
                </p>
                <h2 className="mt-3 font-display text-[2.2rem] leading-none tracking-[-0.04em] text-[var(--text)]">
                  {isLogin ? '欢迎回来' : '创建账号'}
                </h2>
                <p className="mt-3 text-sm leading-6 text-[var(--text-soft)]">
                  {isLogin ? '进入你的训练对话空间。' : '先创建账户，稍后可补充完整档案。'}
                </p>
              </div>
              <div className="rounded-full bg-[var(--mint-soft)] px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--text-soft)]">
                health data
              </div>
            </div>

            <div className="mt-6 grid grid-cols-2 rounded-[1.15rem] bg-[var(--panel-muted)] p-1">
              <button
                type="button"
                onClick={() => setMode('login')}
                className={`rounded-[0.95rem] px-4 py-3 text-sm font-semibold transition-all duration-300 ${
                  isLogin
                    ? 'bg-white text-[var(--text)] shadow-[0_8px_24px_rgba(124,145,138,0.12)]'
                    : 'text-[var(--text-soft)]'
                }`}
              >
                登录
              </button>
              <button
                type="button"
                onClick={() => setMode('register')}
                className={`rounded-[0.95rem] px-4 py-3 text-sm font-semibold transition-all duration-300 ${
                  !isLogin
                    ? 'bg-white text-[var(--text)] shadow-[0_8px_24px_rgba(124,145,138,0.12)]'
                    : 'text-[var(--text-soft)]'
                }`}
              >
                注册
              </button>
            </div>

            {isLogin ? (
              <form className="mt-6" onSubmit={handleLoginSubmit}>
                <div className="space-y-4">
                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-[var(--text-soft)]">
                      邮箱或用户名
                    </span>
                    <input
                      type="text"
                      name="identifier"
                      placeholder="输入 fitmind 或 demo@fitmind.ai"
                      value={loginForm.identifier}
                      onChange={handleLoginInput}
                      className={fieldBaseClass}
                    />
                    <p className="mt-2 min-h-5 text-xs text-[var(--danger)]">{loginErrors.identifier || ' '}</p>
                  </label>

                  <label className="block">
                    <div className="mb-2 flex items-center justify-between gap-4">
                      <span className="text-sm font-medium text-[var(--text-soft)]">密码</span>
                      <button
                        type="button"
                        className="text-xs font-medium text-[var(--text-faint)] transition hover:text-[var(--accent)]"
                      >
                        忘记密码
                      </button>
                    </div>
                    <input
                      type="password"
                      name="password"
                      placeholder="输入默认密码 123456"
                      value={loginForm.password}
                      onChange={handleLoginInput}
                      className={fieldBaseClass}
                    />
                    <p className="mt-2 min-h-5 text-xs text-[var(--danger)]">{loginErrors.password || ' '}</p>
                  </label>
                </div>

                <div className="rounded-[1.3rem] border border-[var(--line)] bg-[rgba(79,140,255,0.05)] px-4 py-3 text-sm leading-6 text-[var(--text-soft)]">
                  默认账号 <span className="font-mono text-[var(--text)]">fitmind</span>，默认密码{' '}
                  <span className="font-mono text-[var(--text)]">123456</span>
                </div>

                <div className="mt-4 min-h-11">
                  {loginStatus.message ? (
                    <p
                      className={`rounded-[1rem] px-3 py-2 text-sm ${
                        loginStatus.type === 'success'
                          ? 'bg-[var(--mint-soft)] text-[var(--text)]'
                          : 'bg-[rgba(215,99,99,0.1)] text-[var(--danger)]'
                      }`}
                    >
                      {loginStatus.message}
                    </p>
                  ) : null}
                </div>

                <button
                  type="submit"
                  disabled={submitting.login}
                  className="mt-2 inline-flex h-13 w-full items-center justify-center rounded-[1.15rem] bg-[linear-gradient(135deg,#5f9bff,#4f8cff_45%,#77c7b0)] px-5 text-sm font-semibold text-white shadow-[0_16px_34px_rgba(79,140,255,0.28)] transition-all duration-300 hover:-translate-y-0.5 hover:shadow-[0_20px_40px_rgba(79,140,255,0.32)] disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {submitting.login ? '登录中...' : '进入 FitMind'}
                </button>

                <p className="mt-4 text-center text-sm text-[var(--text-soft)]">
                  还没有账号？
                  <button
                    type="button"
                    onClick={() => setMode('register')}
                    className="ml-1 font-semibold text-[var(--accent)] transition hover:opacity-80"
                  >
                    立即注册
                  </button>
                </p>
              </form>
            ) : (
              <form className="mt-6" onSubmit={handleRegisterSubmit}>
                <div className="space-y-4">
                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-[var(--text-soft)]">邮箱</span>
                    <input
                      type="email"
                      name="email"
                      placeholder="you@example.com"
                      value={registerForm.email}
                      onChange={handleRegisterInput}
                      className={fieldBaseClass}
                    />
                    <p className="mt-2 min-h-5 text-xs text-[var(--danger)]">{registerErrors.email || ' '}</p>
                  </label>

                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-[var(--text-soft)]">用户名</span>
                    <input
                      type="text"
                      name="username"
                      placeholder="输入你的昵称"
                      value={registerForm.username}
                      onChange={handleRegisterInput}
                      className={fieldBaseClass}
                    />
                    <p className="mt-2 min-h-5 text-xs text-[var(--danger)]">{registerErrors.username || ' '}</p>
                  </label>

                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-[var(--text-soft)]">密码</span>
                    <input
                      type="password"
                      name="password"
                      placeholder="至少 6 位"
                      value={registerForm.password}
                      onChange={handleRegisterInput}
                      className={fieldBaseClass}
                    />
                    <p className="mt-2 min-h-5 text-xs text-[var(--danger)]">{registerErrors.password || ' '}</p>
                  </label>
                </div>

                <div className="mt-4 min-h-11">
                  {registerStatus.message ? (
                    <p
                      className={`rounded-[1rem] px-3 py-2 text-sm ${
                        registerStatus.type === 'success'
                          ? 'bg-[var(--mint-soft)] text-[var(--text)]'
                          : 'bg-[rgba(215,99,99,0.1)] text-[var(--danger)]'
                      }`}
                    >
                      {registerStatus.message}
                    </p>
                  ) : null}
                </div>

                <button
                  type="submit"
                  disabled={submitting.register}
                  className="mt-2 inline-flex h-13 w-full items-center justify-center rounded-[1.15rem] bg-[var(--text)] px-5 text-sm font-semibold text-white shadow-[0_16px_34px_rgba(30,42,40,0.18)] transition-all duration-300 hover:-translate-y-0.5 hover:bg-[#243330] disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {submitting.register ? '注册中...' : '创建账号'}
                </button>

                <p className="mt-4 text-center text-sm text-[var(--text-soft)]">
                  已有账号？
                  <button
                    type="button"
                    onClick={() => setMode('login')}
                    className="ml-1 font-semibold text-[var(--accent)] transition hover:opacity-80"
                  >
                    返回登录
                  </button>
                </p>
              </form>
            )}
          </div>
        </div>
      </section>
    </main>
  )
}

export default LoginExperience
