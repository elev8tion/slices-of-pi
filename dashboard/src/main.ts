import { createApp, ref } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import './assets/main.css'

// Global toast bus
import { createApp as _createApp } from 'vue'

export const toastBus = {
  _add: null as any,
  info(msg: string) { this._add?.(msg, 'info') },
  success(msg: string) { this._add?.(msg, 'success') },
  error(msg: string) { this._add?.(msg, 'error') },
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'dashboard', component: () => import('./views/Dashboard.vue') },
    { path: '/agents', name: 'agents', component: () => import('./views/Agents.vue') },
    { path: '/sessions', name: 'sessions', component: () => import('./views/Sessions.vue') },
    { path: '/schedules', name: 'schedules', component: () => import('./views/Schedules.vue') },
    { path: '/skills', name: 'skills', component: () => import('./views/Skills.vue') },
    { path: '/extensions', name: 'extensions', component: () => import('./views/Extensions.vue') },
    { path: '/templates', name: 'templates', component: () => import('./views/Templates.vue') },
    { path: '/teams', name: 'teams', component: () => import('./views/Teams.vue') },
    { path: '/settings', name: 'settings', component: () => import('./views/Settings.vue') },
  ],
})

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
