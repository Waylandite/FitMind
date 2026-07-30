import { lazy, Suspense, useState } from 'react'

import ChatWorkspace from './pages/ChatWorkspace'
import LoginExperience from './pages/LoginExperience'
import WorkoutHistory from './pages/WorkoutHistory'

const WeeklyTrends = lazy(() => import('./pages/WeeklyTrends'))

function ViewLoading() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#f5f8f6]">
      <div className="text-center">
        <span className="mx-auto block h-10 w-10 animate-spin rounded-full border-2 border-[rgba(79,140,255,0.18)] border-t-[var(--accent)]" />
        <p className="mt-3 text-xs font-bold tracking-[0.18em] text-[var(--text-faint)]">LOADING VIEW</p>
      </div>
    </main>
  )
}

function App() {
  const [session, setSession] = useState(null)
  const [activeView, setActiveView] = useState('chat')

  const handleLogout = () => {
    setSession(null)
    setActiveView('chat')
  }

  if (session) {
    if (activeView === 'workout-history') {
      return <WorkoutHistory session={session} onBackToChat={() => setActiveView('chat')} />
    }
    if (activeView === 'weekly-trends') {
      return (
        <Suspense fallback={<ViewLoading />}>
          <WeeklyTrends session={session} onBackToChat={() => setActiveView('chat')} />
        </Suspense>
      )
    }

    return (
      <ChatWorkspace
        session={session}
        onLogout={handleLogout}
        onOpenHistory={() => setActiveView('workout-history')}
        onOpenWeeklyTrends={() => setActiveView('weekly-trends')}
      />
    )
  }

  return <LoginExperience onLoginSuccess={(nextSession) => {
    setSession(nextSession)
    setActiveView('chat')
  }} />
}

export default App
