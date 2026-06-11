import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { toastBus } from '@/main'

export interface User {
  id: string
  username: string
  email: string
  role: string
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('pi_auth_token'))
  const user = ref<User | null>(null)

  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  // Load user from token on init
  async function loadUser() {
    if (!token.value) return
    try {
      const res = await fetch('/api/auth/me', {
        headers: { Authorization: `Bearer ${token.value}` }
      })
      if (res.ok) {
        user.value = await res.json()
      } else {
        // Token expired or invalid
        token.value = null
        localStorage.removeItem('pi_auth_token')
      }
    } catch {
      // Server might not have auth yet — assume single-user mode
    }
  }

  async function login(username: string, password: string): Promise<boolean> {
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Login failed' }))
        toastBus.error(err.detail || 'Login failed')
        return false
      }
      const data = await res.json()
      token.value = data.token
      user.value = data.user
      localStorage.setItem('pi_auth_token', data.token)
      toastBus.success(`Welcome back, ${data.user.username}`)
      return true
    } catch (e: any) {
      toastBus.error('Login failed: ' + (e.message || 'unknown error'))
      return false
    }
  }

  async function register(username: string, email: string, password: string): Promise<boolean> {
    try {
      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, email, password }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Registration failed' }))
        toastBus.error(err.detail || 'Registration failed')
        return false
      }
      const data = await res.json()
      token.value = data.token
      user.value = data.user
      localStorage.setItem('pi_auth_token', data.token)
      toastBus.success('Account created! Welcome to Slice of Pi.')
      return true
    } catch (e: any) {
      toastBus.error('Registration failed: ' + (e.message || 'unknown error'))
      return false
    }
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('pi_auth_token')
    toastBus.info('Logged out')
  }

  function authHeaders(): Record<string, string> {
    if (token.value) {
      return { Authorization: `Bearer ${token.value}` }
    }
    return {}
  }

  // Auto-detect: if /api/auth/me returns 401, we're in auth mode
  // If it's not found (404) or works without header, we're in no-auth mode
  let _noAuthChecked = false
  let _noAuth = false

  async function checkNoAuth(): Promise<boolean> {
    if (_noAuthChecked) return _noAuth
    _noAuthChecked = true
    try {
      const res = await fetch('/api/auth/me')
      if (res.ok) {
        const u = await res.json()
        user.value = u
        _noAuth = true
        return true
      }
    } catch {
      // auth mode
    }
    _noAuth = false
    return false
  }

  return {
    token, user, isAuthenticated, isAdmin,
    login, register, logout, loadUser, authHeaders, checkNoAuth,
  }
})
