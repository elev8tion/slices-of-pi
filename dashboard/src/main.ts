import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import './assets/main.css'
import { useAuthStore } from './stores/auth'

// Global toast bus
export const toastBus = {
  _add: null as any,
  info(msg: string) { this._add?.(msg, 'info') },
  success(msg: string) { this._add?.(msg, 'success') },
  error(msg: string) { this._add?.(msg, 'error') },
  warning(msg: string) { this._add?.(msg, 'warning') },
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: () => import('./views/Login.vue') },
    { path: '/', name: 'dashboard', component: () => import('./views/Dashboard.vue') },
    { path: '/agents', name: 'agents', component: () => import('./views/Agents.vue') },
    { path: '/sessions', name: 'sessions', component: () => import('./views/Sessions.vue') },
    { path: '/schedules', name: 'schedules', component: () => import('./views/Schedules.vue') },
    { path: '/skills', name: 'skills', component: () => import('./views/Skills.vue') },
    { path: '/extensions', name: 'extensions', component: () => import('./views/Extensions.vue') },
    { path: '/templates', name: 'templates', component: () => import('./views/Templates.vue') },
    { path: '/teams', name: 'teams', component: () => import('./views/Teams.vue') },
    { path: '/console', name: 'console', component: () => import('./views/Console.vue') },
    { path: '/ops', name: 'ops', component: () => import('./views/OperatorRoom.vue') },
    { path: '/replay', name: 'replay', component: () => import('./views/Replay.vue') },
    { path: '/audit', name: 'audit', component: () => import('./views/AuditLog.vue') },
    { path: '/settings', name: 'settings', component: () => import('./views/Settings.vue') },
  ],
})

// Auth guard — redirect to login if not authenticated
router.beforeEach(async (to, from, next) => {
  if (to.path === '/login') {
    next()
    return
  }
  const auth = useAuthStore()
  const isNoAuth = await auth.checkNoAuth()
  if (isNoAuth) {
    next()
    return
  }
  if (auth.isAuthenticated) {
    next()
  } else {
    next('/login')
  }
})

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
app.use(router)

// Load user on init
useAuthStore().loadUser()

app.mount('#app')
