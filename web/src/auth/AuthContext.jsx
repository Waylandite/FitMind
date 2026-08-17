import { useEffect, useState } from 'react'

import {
  apiFetch,
  authFetch,
  clearAccessToken,
  readApiPayload,
  refreshAccessToken,
  setAccessToken,
  setUnauthorizedHandler,
} from '../lib/apiClient'
import AuthContext from './authContext'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [bootstrapping, setBootstrapping] = useState(true)

  useEffect(() => setUnauthorizedHandler(() => setUser(null)), [])

  useEffect(() => {
    let active = true

    const restoreSession = async () => {
      try {
        await refreshAccessToken()
        const currentUser = await readApiPayload(await apiFetch('/auth/me'))
        if (active) setUser(currentUser)
      } catch {
        clearAccessToken()
        if (active) setUser(null)
      } finally {
        if (active) setBootstrapping(false)
      }
    }

    void restoreSession()
    return () => {
      active = false
    }
  }, [])

  const acceptAuthResponse = async (response) => {
    const payload = await readApiPayload(await response)
    setAccessToken(payload.access_token)
    setUser(payload.user)
    return payload.user
  }

  const login = (credentials) =>
    acceptAuthResponse(authFetch('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    }))

  const register = (values) =>
    acceptAuthResponse(authFetch('/auth/register', {
      method: 'POST',
      body: JSON.stringify(values),
    }))

  const logout = async () => {
    try {
      await apiFetch('/auth/logout', { method: 'POST' }, false)
    } finally {
      clearAccessToken()
      setUser(null)
    }
  }

  const changePassword = async (values) => {
    await readApiPayload(await apiFetch('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify(values),
    }))
    clearAccessToken()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, bootstrapping, login, register, logout, changePassword }}>
      {children}
    </AuthContext.Provider>
  )
}
