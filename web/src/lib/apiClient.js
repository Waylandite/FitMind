export const apiBaseUrl =
  import.meta.env.VITE_AGENT_BASE_URL?.replace(/\/$/, '') ?? 'http://127.0.0.1:8000/api/v1'

let accessToken = null
let refreshPromise = null
let unauthorizedHandler = null

export function setAccessToken(token) {
  accessToken = token || null
}

export function clearAccessToken() {
  accessToken = null
}

export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = handler
  return () => {
    if (unauthorizedHandler === handler) unauthorizedHandler = null
  }
}

async function parseResponse(response) {
  if (response.status === 204) return null
  const contentType = response.headers.get('content-type') ?? ''
  return contentType.includes('application/json') ? response.json() : response.text()
}

export async function authFetch(path, options = {}) {
  return fetch(`${apiBaseUrl}${path}`, {
    ...options,
    credentials: 'include',
    headers: {
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...options.headers,
    },
  })
}

export async function refreshAccessToken() {
  if (!refreshPromise) {
    refreshPromise = authFetch('/auth/refresh', { method: 'POST' })
      .then(async (response) => {
        const payload = await parseResponse(response)
        if (!response.ok) throw new Error(payload?.detail ?? '登录状态已过期')
        setAccessToken(payload.access_token)
        return payload
      })
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

export async function apiFetch(path, options = {}, retry = true) {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...options,
    credentials: 'include',
    headers: {
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...options.headers,
    },
  })

  if (response.status !== 401 || !retry) return response

  try {
    await refreshAccessToken()
    return apiFetch(path, options, false)
  } catch (error) {
    clearAccessToken()
    unauthorizedHandler?.(error)
    return response
  }
}

export async function readApiPayload(response) {
  const payload = await parseResponse(response)
  if (!response.ok) {
    throw new Error(payload?.detail ?? payload?.message ?? `请求失败: ${response.status}`)
  }
  return payload
}
