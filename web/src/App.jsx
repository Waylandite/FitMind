import { lazy, Suspense, useState } from 'react'

import useAuth from './auth/useAuth'
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
  const { user, bootstrapping, logout } = useAuth()
  const [activeView, setActiveView] = useState('chat')

  const handleLogout = async () => {
    await logout()
    setActiveView('chat')
  }

  if (bootstrapping) return <ViewLoading />

  if (user) {
    const session = {
      userId: user.id,
      name: user.display_name || user.username,
      identifier: user.email,
    }
    if (activeView === 'workout-history') {
      return <WorkoutHistory onBackToChat={() => setActiveView('chat')} />
    }
    if (activeView === 'weekly-trends') {
      return (
        <Suspense fallback={<ViewLoading />}>
          <WeeklyTrends onBackToChat={() => setActiveView('chat')} />
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

  return <LoginExperience />
}

export default App
