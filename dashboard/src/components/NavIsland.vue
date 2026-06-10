<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { computed } from 'vue'

const route = useRoute()
const router = useRouter()
const store = useAppStore()

const navLinks = [
  { to: '/', label: 'Dashboard' },
  { to: '/agents', label: 'Agents' },
  { to: '/sessions', label: 'Sessions' },
  { to: '/schedules', label: 'Schedules' },
  { to: '/skills', label: 'Skills' },
  { to: '/extensions', label: 'Extensions' },
  { to: '/templates', label: 'Templates' },
  { to: '/teams', label: 'Teams' },
  { to: '/settings', label: 'Settings' },
]

const activeRoute = computed(() => {
  if (route.path === '/') return '/'
  return '/' + (route.path.split('/')[1] || '')
})
</script>

<template>
  <nav class="nav-island fade-up">
    <div class="nav-logo">
      <div class="nav-logo-icon">π</div>
      <span>Slice of Pi</span>
    </div>
    <div class="nav-links">
      <router-link
        v-for="link in navLinks"
        :key="link.to"
        :to="link.to"
        class="nav-link"
        :class="{ active: activeRoute === link.to }"
      >
        {{ link.label }}
      </router-link>
    </div>
    <div class="nav-divider" />
    <div class="nav-actions">
      <div class="connection-dot" :class="{ '!bg-warning': !store.connected }" />
      <span class="connection-label">{{ store.connected ? 'Connected' : 'Offline' }}</span>
    </div>
  </nav>
</template>

<style scoped>
.nav-island {
  position: sticky;
  top: 12px;
  z-index: 100;
  margin: 0 auto;
  width: max-content;
  max-width: calc(100% - 32px);
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 8px 20px 8px 12px;
  background: rgba(12,12,16,0.85);
  backdrop-filter: blur(32px) saturate(1.4);
  -webkit-backdrop-filter: blur(32px) saturate(1.4);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 9999px;
  box-shadow: 0 0 0 1px rgba(255,255,255,0.03), 0 8px 32px rgba(0,0,0,0.6);
  transition: all 0.5s cubic-bezier(0.32,0.72,0,1);
}
.nav-island:hover {
  border-color: rgba(255,255,255,0.1);
  box-shadow: 0 0 0 1px rgba(255,255,255,0.05), 0 12px 48px rgba(0,0,0,0.7);
}
.nav-logo {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 15px;
  letter-spacing: -0.02em;
  padding: 4px 12px 4px 4px;
  border-right: 1px solid rgba(255,255,255,0.06);
  margin-right: 4px;
  color: #F0F0F2;
  text-decoration: none;
}
.nav-logo-icon {
  width: 28px;
  height: 28px;
  background: #6366F1;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
  color: #fff;
}
.nav-links {
  display: flex;
  align-items: center;
  gap: 2px;
}
.nav-link {
  font-size: 12.5px;
  font-weight: 500;
  letter-spacing: 0.01em;
  padding: 6px 14px;
  border-radius: 8px;
  color: rgba(255,255,255,0.45);
  text-decoration: none;
  transition: all 0.4s cubic-bezier(0.32,0.72,0,1);
}
.nav-link:hover {
  color: rgba(255,255,255,0.8);
  background: rgba(255,255,255,0.04);
}
.nav-link.active {
  color: #fff;
  background: rgba(99,102,241,0.12);
}
.nav-divider {
  width: 1px;
  height: 20px;
  background: rgba(255,255,255,0.06);
}
.nav-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-left: 4px;
}
.connection-dot {
  width: 8px;
  height: 8px;
  border-radius: 9999px;
  background: #22C55E;
  box-shadow: 0 0 8px rgba(34,197,94,0.4);
  animation: pulseDot 2s ease-in-out infinite;
}
.connection-label {
  font-size: 11px;
  color: rgba(255,255,255,0.35);
  font-weight: 500;
}

@media (max-width: 768px) {
  .nav-links { display: none; }
  .nav-logo { border-right: none; }
  .connection-label { display: none; }
  .nav-island {
    width: calc(100% - 16px);
    padding: 6px 14px 6px 8px;
    gap: 12px;
  }
}
</style>
