import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, render, waitFor, screen } from '@testing-library/react'
import { AuthProvider, useAuth } from './AuthContext'
import type { ReactNode } from 'react'

const mockApiFetch = vi.fn()
const mockGetToken = vi.fn()
const mockSetToken = vi.fn()
const mockRemoveToken = vi.fn()
const mockStoreUser = vi.fn()
const mockGetStoredUser = vi.fn()

vi.mock('@/lib/auth', () => ({
  apiFetch: (...args: any[]) => mockApiFetch(...args),
  getToken: (...args: any[]) => mockGetToken(...args),
  setToken: (...args: any[]) => mockSetToken(...args),
  removeToken: (...args: any[]) => mockRemoveToken(...args),
  storeUser: (...args: any[]) => mockStoreUser(...args),
  getStoredUser: (...args: any[]) => mockGetStoredUser(...args),
}))

function renderWithProvider(ui: ReactNode) {
  return render(<AuthProvider>{ui}</AuthProvider>)
}

describe('AuthProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('initial state without token', () => {
    beforeEach(() => {
      mockGetStoredUser.mockReturnValue(null)
      mockGetToken.mockReturnValue(null)
    })

    it('sets isLoading to false and user to null', async () => {
      const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })
      await waitFor(() => expect(result.current.isLoading).toBe(false))
      expect(result.current.user).toBeNull()
    })
  })

  describe('initial state with stored user', () => {
    beforeEach(() => {
      mockGetStoredUser.mockReturnValue({ id: 'u1', email: 'a@b.com' })
      mockGetToken.mockReturnValue('valid-token')
      mockApiFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({ id: 'u1', email: 'a@b.com' }) })
    })

    it('loads user from /api/auth/me on mount', async () => {
      const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })
      await waitFor(() => expect(result.current.isLoading).toBe(false))
      expect(result.current.user).toEqual({ id: 'u1', email: 'a@b.com' })
      expect(mockApiFetch).toHaveBeenCalledWith('/api/auth/me')
    })

    it('clears user when /api/auth/me fails', async () => {
      mockApiFetch.mockResolvedValue({ ok: false })
      const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })
      await waitFor(() => expect(result.current.isLoading).toBe(false))
      expect(result.current.user).toBeNull()
      expect(mockRemoveToken).toHaveBeenCalled()
    })

    it('clears user when /api/auth/me throws', async () => {
      mockApiFetch.mockRejectedValue(new Error('network'))
      const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })
      await waitFor(() => expect(result.current.isLoading).toBe(false))
      expect(result.current.user).toBeNull()
      expect(mockRemoveToken).toHaveBeenCalled()
    })
  })

  describe('login', () => {
    beforeEach(() => {
      mockGetStoredUser.mockReturnValue(null)
      mockGetToken.mockReturnValue(null)
    })

    it('sets user and token on successful login', async () => {
      mockApiFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ access_token: 'tok-123', user_id: 'u1' }),
      })
      const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })
      await waitFor(() => expect(result.current.isLoading).toBe(false))
      await result.current.login('a@b.com', 'pass')
      expect(mockApiFetch).toHaveBeenCalledWith('/api/auth/login', expect.objectContaining({ method: 'POST' }))
      expect(mockSetToken).toHaveBeenCalledWith('tok-123')
      expect(mockStoreUser).toHaveBeenCalledWith({ id: 'u1', email: 'a@b.com' })
      await waitFor(() => expect(result.current.user).toEqual({ id: 'u1', email: 'a@b.com' }))
    })

    it('throws on failed login', async () => {
      mockApiFetch.mockResolvedValue({
        ok: false,
        json: () => Promise.resolve({ detail: 'Invalid credentials' }),
      })
      const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })
      await waitFor(() => expect(result.current.isLoading).toBe(false))
      await expect(result.current.login('a@b.com', 'wrong')).rejects.toThrow('Invalid credentials')
    })

    it('throws generic error when API returns no detail', async () => {
      mockApiFetch.mockResolvedValue({
        ok: false,
        json: () => Promise.reject(new Error('parse error')),
      })
      const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })
      await waitFor(() => expect(result.current.isLoading).toBe(false))
      await expect(result.current.login('a@b.com', 'wrong')).rejects.toThrow('Login failed')
    })
  })

  describe('register', () => {
    beforeEach(() => {
      mockGetStoredUser.mockReturnValue(null)
      mockGetToken.mockReturnValue(null)
    })

    it('sets user and token on successful registration', async () => {
      mockApiFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ access_token: 'tok-456', user_id: 'u2' }),
      })
      const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })
      await waitFor(() => expect(result.current.isLoading).toBe(false))
      await result.current.register('b@c.com', 'pass', 'Bob')
      expect(mockApiFetch).toHaveBeenCalledWith('/api/auth/register', expect.objectContaining({ method: 'POST' }))
      expect(mockSetToken).toHaveBeenCalledWith('tok-456')
      expect(mockStoreUser).toHaveBeenCalledWith({ id: 'u2', email: 'b@c.com', display_name: 'Bob' })
      await waitFor(() => expect(result.current.user).toEqual({ id: 'u2', email: 'b@c.com', display_name: 'Bob' }))
    })
  })

  describe('logout', () => {
    beforeEach(() => {
      mockGetStoredUser.mockReturnValue(null)
      mockGetToken.mockReturnValue(null)
    })

    it('clears user and token', async () => {
      const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })
      await waitFor(() => expect(result.current.isLoading).toBe(false))
      result.current.logout()
      expect(mockRemoveToken).toHaveBeenCalled()
      expect(result.current.user).toBeNull()
    })
  })
})

describe('useAuth', () => {
  it('throws when used outside AuthProvider', () => {
    expect(() => renderHook(() => useAuth())).toThrow('useAuth must be used within AuthProvider')
  })

  it('returns context inside AuthProvider', () => {
    mockGetStoredUser.mockReturnValue(null)
    mockGetToken.mockReturnValue(null)
    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })
    expect(result.current).toHaveProperty('user')
    expect(result.current).toHaveProperty('login')
    expect(result.current).toHaveProperty('register')
    expect(result.current).toHaveProperty('logout')
  })
})
