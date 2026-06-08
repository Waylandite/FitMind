import { useState } from 'react'

import ChatWorkspace from './pages/ChatWorkspace'
import LoginExperience from './pages/LoginExperience'

function App() {
  const [session, setSession] = useState(null)

  if (session) {
    return (
      <ChatWorkspace
        session={session}
        onLogout={() => setSession(null)}
      />
    )
  }

  return <LoginExperience onLoginSuccess={setSession} />
}

export default App
