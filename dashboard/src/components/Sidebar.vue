<script setup lang="ts">
import { useRoute } from 'vue-router'
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '@/stores/app'
import StatusIndicator from './StatusIndicator.vue'

const route = useRoute()
const store = useAppStore()

const isActive = (path: string) => route.path === path
const collapsed = computed(() => store.sidebarCollapsed)

const opsPending = ref(0)
let opsPoll: ReturnType<typeof setInterval> | null = null

async function fetchOpsPending() {
  try {
    const res = await fetch('/api/operator-queue/stats')
    const data = await res.json()
    opsPending.value = data.pending || 0
  } catch {}
}

function handleResize() {
  const shouldCollapse = window.innerWidth < 1100
  if (shouldCollapse !== store.sidebarCollapsed) {
    store.toggleSidebar()
  }
}

onMounted(() => {
  fetchOpsPending()
  opsPoll = setInterval(fetchOpsPending, 15000)
  window.addEventListener('resize', handleResize)
  if (window.innerWidth < 1100 && !store.sidebarCollapsed) {
    store.toggleSidebar()
  }
})

onUnmounted(() => {
  if (opsPoll) clearInterval(opsPoll)
  window.removeEventListener('resize', handleResize)
})
</script>

<template>
  <aside class="sidebar" :class="{ collapsed }">
    <!-- Logo — click to toggle collapse/expand -->
    <div class="sidebar-logo" @click="store.toggleSidebar()" role="button" tabindex="0">
      <img v-if="!collapsed" src="/logo-login.png" alt="Slice of Pi" class="sidebar-logo-img" />
      <img v-else src="/logo-nav.png" alt="π" class="sidebar-logo-icon" />
    </div>
    <div class="sidebar-divider" />

    <div class="sidebar-section">
      <div v-if="!collapsed" class="sidebar-label">Saved Views</div>
      <router-link to="/" class="sidebar-item" :class="{ active: isActive('/') }" :title="collapsed ? 'All Agents' : ''">
        <span class="sidebar-icon">◈</span>
        <span v-if="!collapsed">All Agents</span>
        <span class="badge" v-if="!collapsed">{{ store.agents.length }}</span>
      </router-link>
      <div class="sidebar-item" :title="collapsed ? 'Online' : ''">
        <span class="sidebar-icon" style="color:#22C55E">●</span>
        <span v-if="!collapsed">Online</span>
        <span class="badge" v-if="!collapsed" style="color:#22C55E">{{ store.onlineAgents }}</span>
      </div>
      <router-link to="/ops" class="sidebar-item" :class="{ active: isActive('/ops') }" :title="collapsed ? 'Needs Attention' : ''">
        <span class="sidebar-icon" :style="{ color: opsPending > 0 ? '#F59E0B' : 'rgba(233,236,224,0.35)' }">!</span>
        <span v-if="!collapsed">Needs Attention</span>
        <span class="badge" v-if="!collapsed" :style="{ color: opsPending > 0 ? '#F59E0B' : 'rgba(233,236,224,0.35)' }">{{ opsPending > 0 ? opsPending : (store.errorAgents || '0') }}</span>
      </router-link>
    </div>

    <div class="sidebar-divider" />

    <div class="sidebar-section">
      <div v-if="!collapsed" class="sidebar-label">System</div>
      <div class="sidebar-item" :title="collapsed ? 'Status' : ''">
        <span class="sidebar-icon">
          <StatusIndicator :status="store.connected ? 'online' : 'offline'" size="sm" />
        </span>
        <span v-if="!collapsed">{{ store.connected ? 'Connected' : 'Offline' }}</span>
      </div>
      <div class="sidebar-item" :title="collapsed ? 'Agents' : ''">
        <span class="sidebar-icon">⊞</span>
        <span v-if="!collapsed">Agents: {{ store.agents.length }}</span>
      </div>
      <div class="sidebar-item" :title="collapsed ? 'Busy' : ''">
        <span class="sidebar-icon">⚙</span>
        <span v-if="!collapsed">Busy: {{ store.busyAgents }}</span>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 220px;
  min-width: 220px;
  padding-right: 20px;
  padding-top: 8px;
  transition: all 0.3s cubic-bezier(0.32,0.72,0,1);
  overflow: hidden;
}
.sidebar.collapsed {
  width: 60px;
  min-width: 60px;
  padding-right: 8px;
}

.sidebar-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px 0 8px;
  cursor: pointer;
  transition: all 0.3s ease;
}
.sidebar-logo:hover {
  opacity: 0.8;
}
.sidebar-logo-img {
  width: 100px;
  height: 100px;
  border-radius: 16px;
}
.sidebar-logo-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
}

.sidebar-section {
  margin-bottom: 24px;
}
.sidebar-label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(233,236,224,0.25);
  margin-bottom: 10px;
  padding-left: 10px;
  white-space: nowrap;
}
.sidebar-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 10px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 500;
  color: rgba(233,236,224,0.45);
  transition: all 0.3s cubic-bezier(0.32,0.72,0,1);
  margin-bottom: 2px;
  text-decoration: none;
  white-space: nowrap;
}
.sidebar-item:hover {
  color: rgba(233,236,224,0.75);
  background: rgba(233,236,224,0.04);
}
.sidebar-item.active {
  color: #E9ECE0;
  background: rgba(157,213,34,0.12);
}
.sidebar-icon {
  font-size: 14px;
  width: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.sidebar-item .badge {
  margin-left: auto;
  background: rgba(233,236,224,0.06);
  padding: 1px 7px;
  border-radius: 9999px;
  font-size: 10px;
  font-weight: 600;
  color: rgba(233,236,224,0.35);
}
.sidebar-divider {
  height: 1px;
  background: rgba(233,236,224,0.04);
  margin: 16px 10px;
}

@media (max-width: 968px) {
  .sidebar { display: none; }
}
</style>
