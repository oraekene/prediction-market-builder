import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'
import { apiFetch, getToken, setToken, removeToken, storeUser, getStoredUser } from '@/lib/auth'

interface User {
  id: string
  email: string
  display_name?: string
}

interface AuthContextType {
  user: User | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, display_name?: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(getStoredUser)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const token = getToken()
    if (!token) {
      setIsLoading(false)
      return
    }
    apiFetch('/api/auth/me')
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((u) => {
        setUser(u)
        storeUser(u)
      })
      .catch(() => {
        removeToken()
        setUser(null)
      })
      .finally(() => setIsLoading(false))
  }, [])

  const login = async (email: string, password: string) => {
    const res = await apiFetch('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Login failed' }))
      throw new Error(err.detail)
    }
    const data = await res.json()
    setToken(data.access_token)
    const u = { id: data.user_id, email }
    storeUser(u)
    setUser(u)
  }

  const register = async (email: string, password: string, display_name?: string) => {
    const res = await apiFetch('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, display_name }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Registration failed' }))
      throw new Error(err.detail)
    }
    const data = await res.json()
    setToken(data.access_token)
    const u = { id: data.user_id, email, display_name }
    storeUser(u)
    setUser(u)
  }

  const logout = () => {
    removeToken()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
