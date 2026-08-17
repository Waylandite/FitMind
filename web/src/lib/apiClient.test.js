import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  apiFetch,
  clearAccessToken,
  setAccessToken,
  setUnauthorizedHandler,
} from './apiClient'


function jsonResponse(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}


afterEach(() => {
  clearAccessToken()
  setUnauthorizedHandler(null)
  vi.unstubAllGlobals()
})


describe('apiFetch', () => {
  it('attaches the in-memory access token', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }))
    vi.stubGlobal('fetch', fetchMock)
    setAccessToken('access-token')

    const response = await apiFetch('/auth/me')

    expect(response.status).toBe(200)
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe('Bearer access-token')
  })

  it('refreshes once and retries a request after 401', async () => {
    const fetchMock = vi.fn(async (url, options) => {
      if (url.endsWith('/auth/refresh')) {
        return jsonResponse({ access_token: 'fresh-token', user: { id: 1 } })
      }
      if (options.headers.Authorization === 'Bearer fresh-token') {
        return jsonResponse({ sessions: [] })
      }
      return jsonResponse({ detail: 'expired' }, 401)
    })
    vi.stubGlobal('fetch', fetchMock)
    setAccessToken('expired-token')

    const response = await apiFetch('/memories/sessions')

    expect(response.status).toBe(200)
    expect(fetchMock).toHaveBeenCalledTimes(3)
    expect(fetchMock.mock.calls[2][1].headers.Authorization).toBe('Bearer fresh-token')
  })

  it('shares one refresh request across concurrent 401 responses', async () => {
    let refreshCount = 0
    const fetchMock = vi.fn(async (url, options) => {
      if (url.endsWith('/auth/refresh')) {
        refreshCount += 1
        await new Promise((resolve) => setTimeout(resolve, 5))
        return jsonResponse({ access_token: 'fresh-token', user: { id: 1 } })
      }
      return options.headers.Authorization === 'Bearer fresh-token'
        ? jsonResponse({ ok: true })
        : jsonResponse({ detail: 'expired' }, 401)
    })
    vi.stubGlobal('fetch', fetchMock)
    setAccessToken('expired-token')

    const responses = await Promise.all([
      apiFetch('/memories/sessions'),
      apiFetch('/profiles/me'),
    ])

    expect(responses.every((response) => response.ok)).toBe(true)
    expect(refreshCount).toBe(1)
  })

  it('notifies the auth boundary when refresh fails', async () => {
    const onUnauthorized = vi.fn()
    setUnauthorizedHandler(onUnauthorized)
    vi.stubGlobal('fetch', vi.fn(async (url) => (
      url.endsWith('/auth/refresh')
        ? jsonResponse({ detail: 'expired' }, 401)
        : jsonResponse({ detail: 'expired' }, 401)
    )))
    setAccessToken('expired-token')

    const response = await apiFetch('/profiles/me')

    expect(response.status).toBe(401)
    expect(onUnauthorized).toHaveBeenCalledOnce()
  })
})
