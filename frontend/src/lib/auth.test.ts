import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { getToken, setToken, removeToken, isAuthenticated, getStoredUser, storeUser, apiFetch } from './auth'

const TOKEN_KEY = 'pm_builder_token'
const USER_KEY = 'pm_builder_user'

beforeEach(() => {
  localStorage.clear()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('getToken', () => {
  it('returns null when no token', () => {
    expect(getToken()).toBeNull()
  })

  it('returns stored token', () => {
    localStorage.setItem(TOKEN_KEY, 'test-token')
    expect(getToken()).toBe('test-token')
  })
})

describe('setToken', () => {
  it('stores token in localStorage', () => {
    setToken('my-token')
    expect(localStorage.getItem(TOKEN_KEY)).toBe('my-token')
  })
})

describe('removeToken', () => {
  it('removes token and user from localStorage', () => {
    localStorage.setItem(TOKEN_KEY, 't')
    localStorage.setItem(USER_KEY, '{"id":"1"}')
    removeToken()
    expect(localStorage.getItem(TOKEN_KEY)).toBeNull()
    expect(localStorage.getItem(USER_KEY)).toBeNull()
  })
})

describe('isAuthenticated', () => {
  it('returns false when no token', () => {
    expect(isAuthenticated()).toBe(false)
  })

  it('returns true when token exists', () => {
    localStorage.setItem(TOKEN_KEY, 't')
    expect(isAuthenticated()).toBe(true)
  })
})

describe('getStoredUser', () => {
  it('returns null when no user stored', () => {
    expect(getStoredUser()).toBeNull()
  })

  it('parses stored user JSON', () => {
    const user = { id: '1', email: 'a@b.com' }
    localStorage.setItem(USER_KEY, JSON.stringify(user))
    expect(getStoredUser()).toEqual(user)
  })

  it('returns null on invalid JSON', () => {
    localStorage.setItem(USER_KEY, '{broken}')
    expect(getStoredUser()).toBeNull()
  })
})

describe('storeUser', () => {
  it('stores user as JSON', () => {
    const user = { id: '1', email: 'a@b.com', display_name: 'Alice' }
    storeUser(user)
    expect(JSON.parse(localStorage.getItem(USER_KEY)!)).toEqual(user)
  })
})

describe('apiFetch', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
    vi.stubGlobal('location', { href: '' })
  })

  it('adds Bearer token when available', async () => {
    localStorage.setItem(TOKEN_KEY, 'my-jwt')
    vi.mocked(fetch).mockResolvedValue(new Response('{}', { status: 200 }))
    await apiFetch('/api/test')
    expect(fetch).toHaveBeenCalledWith('/api/test', {
      headers: { Authorization: 'Bearer my-jwt' },
    })
  })

  it('adds Content-Type for JSON body', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response('{}', { status: 200 }))
    await apiFetch('/api/test', { body: '{"key":"val"}' })
    expect(fetch).toHaveBeenCalledWith('/api/test', {
      body: '{"key":"val"}',
      headers: { 'Content-Type': 'application/json' },
    })
  })

  it('merges custom headers', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response('{}', { status: 200 }))
    await apiFetch('/api/test', { headers: { 'X-Custom': 'val' } })
    expect(fetch).toHaveBeenCalledWith('/api/test', {
      headers: { 'X-Custom': 'val' },
    })
  })

  it('redirects to /login on 401 for non-auth routes', async () => {
    localStorage.setItem(TOKEN_KEY, 'expired')
    vi.mocked(fetch).mockResolvedValue(new Response('Unauthorized', { status: 401 }))
    await apiFetch('/api/markets')
    expect(localStorage.getItem(TOKEN_KEY)).toBeNull()
    expect(window.location.href).toBe('/login')
  })

  it('does not redirect on 401 for auth routes', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response('Unauthorized', { status: 401 }))
    await apiFetch('/api/auth/login')
    expect(window.location.href).not.toBe('/login')
  })

  it('returns response on success', async () => {
    const res = new Response('ok', { status: 200 })
    vi.mocked(fetch).mockResolvedValue(res)
    const result = await apiFetch('/api/test')
    expect(result.status).toBe(200)
  })
})
