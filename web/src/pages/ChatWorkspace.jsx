import { useState } from 'react'

const starterMessages = [
  {
    id: 'm1',
    role: 'assistant',
    title: '今日入口',
    content:
      '我是 FitMind。你可以直接告诉我今天的训练计划、实际完成情况、身体状态或饮食内容，我会帮你整理成结构化记录。',
  },
  {
    id: 'm2',
    role: 'assistant',
    title: '示例',
    content:
      '例如：今天练胸肩三头，卧推 5 组，状态一般，午饭吃了鸡胸和米饭。',
  },
]

const quickPrompts = [
  '记录今天的训练计划',
  '补一条饮食记录',
  '总结今天的状态',
  '回顾最近三天训练',
]

function buildReply(input) {
  if (input.includes('饮食')) {
    return '已识别为饮食记录。我会提取餐次、食物、补剂和大致摄入量，随后准备落库。'
  }

  if (input.includes('状态') || input.includes('疲劳') || input.includes('睡眠')) {
    return '已识别为身体状态记录。我会整理睡眠、疲劳、疼痛和主观恢复感。'
  }

  if (input.includes('完成') || input.includes('做了') || input.includes('训练')) {
    return '已识别为训练执行记录。我会拆分动作、组数、次数、负重和完成度。'
  }

  return '已收到这条自然语言记录。我会继续追问必要字段，并同步准备结构化落库。'
}

function ChatWorkspace({ session, onLogout }) {
  const [messages, setMessages] = useState(starterMessages)
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)

  const handleSend = async (prefill) => {
    const text = (prefill ?? draft).trim()

    if (!text) {
      return
    }

    const userMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text,
    }

    setMessages((current) => [...current, userMessage])
    setDraft('')
    setSending(true)

    await new Promise((resolve) => window.setTimeout(resolve, 520))

    const reply = {
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      title: 'FitMind',
      content: buildReply(text),
    }

    setMessages((current) => [...current, reply])
    setSending(false)
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#07110f] text-[var(--ink-dark)]">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(141,213,186,0.18),transparent_24%),radial-gradient(circle_at_bottom_right,rgba(210,167,105,0.12),transparent_22%),linear-gradient(180deg,#07110f_0%,#0d1715_100%)]" />
      <div className="grid-noise absolute inset-0 opacity-30" />

      <div className="relative flex min-h-screen">
        <aside className="hidden w-[18rem] shrink-0 flex-col border-r border-white/8 bg-[rgba(255,248,241,0.03)] px-5 py-5 backdrop-blur xl:flex">
          <div className="rounded-[1.6rem] border border-white/10 bg-white/[0.04] p-4">
            <p className="font-mono text-[0.66rem] uppercase tracking-[0.28em] text-emerald-100/70">
              FitMind
            </p>
            <h1 className="mt-3 font-display text-[2rem] leading-none text-[var(--ink-dark)]">
              健身对话台
            </h1>
            <p className="mt-3 text-sm leading-6 text-stone-300">
              用自然语言记录训练、饮食与恢复，让每次对话都留下结构化痕迹。
            </p>
          </div>

          <div className="mt-4 rounded-[1.5rem] border border-white/10 bg-white/[0.035] p-4">
            <p className="font-mono text-[0.62rem] uppercase tracking-[0.26em] text-stone-300/60">
              当前身份
            </p>
            <p className="mt-3 text-lg text-stone-100">{session.name}</p>
            <p className="mt-1 text-sm text-stone-400">{session.identifier}</p>
          </div>

          <div className="mt-4 space-y-3">
            {quickPrompts.map((prompt) => (
              <button
                key={prompt}
                type="button"
                onClick={() => handleSend(prompt)}
                className="chat-side-button w-full text-left"
              >
                {prompt}
              </button>
            ))}
          </div>

          <button
            type="button"
            onClick={onLogout}
            className="glass-button mt-auto w-full justify-center"
          >
            退出登录
          </button>
        </aside>

        <section className="flex min-w-0 flex-1 flex-col px-4 py-4 sm:px-6 sm:py-5 lg:px-7">
          <div className="mx-auto flex w-full max-w-[1100px] flex-1 flex-col rounded-[2rem] border border-white/10 bg-[rgba(255,248,241,0.04)] shadow-[0_30px_120px_rgba(0,0,0,0.24)] backdrop-blur">
            <header className="flex items-center justify-between border-b border-white/8 px-5 py-4 sm:px-6">
              <div>
                <p className="font-mono text-[0.62rem] uppercase tracking-[0.3em] text-emerald-100/70">
                  FitMind Chat
                </p>
                <h2 className="mt-2 text-[1.15rem] text-stone-100 sm:text-[1.3rem]">
                  今天想记录什么？
                </h2>
              </div>

              <div className="hidden items-center gap-3 rounded-full border border-white/10 bg-white/[0.05] px-3 py-2 text-sm text-stone-300 sm:flex">
                <span className="h-2 w-2 rounded-full bg-emerald-300 shadow-[0_0_12px_rgba(110,231,183,0.9)]" />
                已连接对话记忆
              </div>
            </header>

            <div className="flex-1 overflow-y-auto px-4 py-5 sm:px-6">
              <div className="mx-auto flex max-w-[860px] flex-col gap-4">
                {messages.map((message) => (
                  <article
                    key={message.id}
                    className={
                      message.role === 'assistant'
                        ? 'chat-message chat-message-assistant'
                        : 'chat-message chat-message-user'
                    }
                  >
                    {message.title && (
                      <p className="font-mono text-[0.62rem] uppercase tracking-[0.28em] text-stone-400">
                        {message.title}
                      </p>
                    )}
                    <p className="mt-2 text-[0.98rem] leading-7 text-current">
                      {message.content}
                    </p>
                  </article>
                ))}

                {sending && (
                  <article className="chat-message chat-message-assistant">
                    <p className="font-mono text-[0.62rem] uppercase tracking-[0.28em] text-stone-400">
                      FitMind
                    </p>
                    <div className="mt-3 flex items-center gap-2">
                      <span className="chat-dot" />
                      <span className="chat-dot [animation-delay:120ms]" />
                      <span className="chat-dot [animation-delay:240ms]" />
                    </div>
                  </article>
                )}
              </div>
            </div>

            <footer className="border-t border-white/8 px-4 py-4 sm:px-6">
              <div className="mx-auto flex max-w-[860px] flex-col gap-3">
                <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
                  {quickPrompts.map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      onClick={() => handleSend(prompt)}
                      className="chat-prompt-chip"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>

                <div className="chat-composer">
                  <textarea
                    value={draft}
                    onChange={(event) => setDraft(event.target.value)}
                    placeholder="例如：今天练腿，深蹲 5 组，状态不错，晚饭吃了牛肉和米饭。"
                    className="min-h-[88px] flex-1 resize-none bg-transparent text-[0.98rem] leading-7 text-stone-100 outline-none placeholder:text-stone-400"
                  />
                  <div className="flex items-center justify-between gap-4">
                    <p className="text-sm text-stone-400">
                      FitMind 会把训练、状态和饮食整理成结构化事实。
                    </p>
                    <button
                      type="button"
                      onClick={() => handleSend()}
                      disabled={sending}
                      className="shine-button shrink-0 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {sending ? '发送中...' : '发送记录'}
                    </button>
                  </div>
                </div>
              </div>
            </footer>
          </div>
        </section>
      </div>
    </main>
  )
}

export default ChatWorkspace
