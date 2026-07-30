import { useState } from 'react'

import ChatWorkspace from './pages/ChatWorkspace'
import LoginExperience from './pages/LoginExperience'
import WorkoutHistory from './pages/WorkoutHistory'

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

    return (
      <ChatWorkspace
        session={session}
        onLogout={handleLogout}
        onOpenHistory={() => setActiveView('workout-history')}
      />
    )
  }

  return <LoginExperience onLoginSuccess={(nextSession) => {
    setSession(nextSession)
    setActiveView('chat')
  }} />
}

export default App
