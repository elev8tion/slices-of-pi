<script setup lang="ts">
import { useRoute } from 'vue-router'
import { computed } from 'vue'
import { useAppStore } from '@/stores/app'

const route = useRoute()
const store = useAppStore()

const isActive = (path: string) => route.path === path
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar-section">
      <div class="sidebar-label">Saved Views</div>
      <router-link to="/" class="sidebar-item" :class="{ active: isActive('/') }">
        All Agents
        <span class="badge">{{ store.agents.length }}</span>
      </router-link>
      <div class="sidebar-item">
        Online
        <span class="badge" style="color:#22C55E">{{ store.onlineAgents }}</span>
      </div>
      <div class="sidebar-item">
        Needs Attention
        <span class="badge" style="color:#EF4444">{{ store.errorAgents }}</span>
      </div>
    </div>
    <div class="sidebar-divider" />
    <div class="sidebar-section">
      <div class="sidebar-label">System</div>
      <div class="sidebar-item">
        <span class="status-dot" :class="store.connected ? 'online' : 'offline'" />
        {{ store.connected ? 'Connected' : 'Offline' }}
      </div>
      <div class="sidebar-item">
        Agents: {{ store.agents.length }}
      </div>
      <div class="sidebar-item">
        Busy: {{ store.busyAgents }}
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
}
.sidebar-section {
  margin-bottom: 24px;
}
.sidebar-label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(255,255,255,0.25);
  margin-bottom: 10px;
  padding-left: 10px;
}
.sidebar-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 10px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 500;
  color: rgba(255,255,255,0.45);
  transition: all 0.3s cubic-bezier(0.32,0.72,0,1);
  margin-bottom: 2px;
  text-decoration: none;
}
.sidebar-item:hover {
  color: rgba(255,255,255,0.75);
  background: rgba(255,255,255,0.04);
}
.sidebar-item.active {
  color: #fff;
  background: rgba(255,255,255,0.06);
}
.sidebar-item .badge {
  margin-left: auto;
  background: rgba(255,255,255,0.06);
  padding: 1px 7px;
  border-radius: 9999px;
  font-size: 10px;
  font-weight: 600;
  color: rgba(255,255,255,0.35);
}
.sidebar-divider {
  height: 1px;
  background: rgba(255,255,255,0.04);
  margin: 16px 10px;
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 9999px;
  flex-shrink: 0;
}
.status-dot.online {
  background: #22C55E;
  box-shadow: 0 0 8px rgba(34,197,94,0.4);
}
.status-dot.offline {
  background: #6B7280;
}

@media (max-width: 968px) {
  .sidebar { display: none; }
}
</style>
