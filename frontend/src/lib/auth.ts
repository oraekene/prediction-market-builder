const TOKEN_KEY = 'pm_builder_token'
const USER_KEY = 'pm_builder_user'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function removeToken() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export function isAuthenticated(): boolean {
  return !!getToken()
}

export function getStoredUser(): { id: string; email: string; display_name?: string } | null {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || 'null')
  } catch {
    return null
  }
}

export function storeUser(user: { id: string; email: string; display_name?: string }) {
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export async function apiFetch(url: string, options?: RequestInit): Promise<Response> {
  const token = getToken()
  const headers: Record<string, string> = {}
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  if (options?.headers) {
    Object.assign(headers, options.headers)
  }
  if (options?.body && typeof options.body === 'string' && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }
  const res = await fetch(url, { ...options, headers })
  if (res.status === 401 && !url.includes('/auth/')) {
    removeToken()
    window.location.href = '/login'
  }
  return res
}
