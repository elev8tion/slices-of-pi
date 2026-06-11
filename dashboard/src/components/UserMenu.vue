<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const open = ref(false)

function toggle() {
  open.value = !open.value
}

function handleLogout() {
  auth.logout()
  open.value = false
  router.push('/login')
}

function close() {
  open.value = false
}
</script>

<template>
  <div class="user-menu" v-click-outside="close">
    <button class="user-trigger" @click="toggle" :title="auth.user?.username || 'User'">
      <div class="user-avatar">
        {{ (auth.user?.username || '?')[0].toUpperCase() }}
      </div>
      <span v-if="auth.user" class="user-name">{{ auth.user.username }}</span>
      <span v-if="auth.isAdmin" class="admin-badge">Admin</span>
    </button>

    <div v-if="open" class="user-dropdown">
      <div class="dropdown-header">
        <div class="dropdown-name">{{ auth.user?.username || 'User' }}</div>
        <div class="dropdown-email">{{ auth.user?.email || '' }}</div>
        <div v-if="auth.isAdmin" class="dropdown-role">Administrator</div>
      </div>
      <div class="dropdown-divider" />
      <button class="dropdown-item" @click="handleLogout">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
        </svg>
        Sign Out
      </button>
    </div>
  </div>
</template>

<style scoped>
.user-menu {
  position: relative;
}
.user-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  background: none;
  border: none;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 8px;
  transition: background 0.2s;
}
.user-trigger:hover {
  background: rgba(255,255,255,0.04);
}
.user-avatar {
  width: 26px;
  height: 26px;
  border-radius: 8px;
  background: rgba(157,213,34,0.2);
  color: #9DD522;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
}
.user-name {
  font-size: 11px;
  color: rgba(255,255,255,0.5);
  font-weight: 500;
}
.admin-badge {
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 1px 6px;
  border-radius: 4px;
  background: rgba(245,158,11,0.12);
  color: #F59E0B;
}

.user-dropdown {
  position: absolute;
  right: 0;
  top: calc(100% + 8px);
  min-width: 200px;
  background: #0C0C10;
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 12px;
  box-shadow: 0 12px 40px rgba(0,0,0,0.6);
  z-index: 300;
  overflow: hidden;
}
.dropdown-header {
  padding: 14px 16px;
}
.dropdown-name {
  font-size: 13px;
  font-weight: 600;
  color: #F0F0F2;
}
.dropdown-email {
  font-size: 11px;
  color: rgba(255,255,255,0.3);
  margin-top: 2px;
}
.dropdown-role {
  font-size: 10px;
  font-weight: 600;
  color: #F59E0B;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-top: 4px;
}
.dropdown-divider {
  height: 1px;
  background: rgba(255,255,255,0.04);
}
.dropdown-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  font-size: 12px;
  color: rgba(255,255,255,0.5);
  background: none;
  border: none;
  cursor: pointer;
  transition: background 0.2s;
}
.dropdown-item:hover {
  background: rgba(255,255,255,0.04);
  color: rgba(255,255,255,0.8);
}
</style>

<script lang="ts">
// v-click-outside directive
export default {
  directives: {
    clickOutside: {
      mounted(el: HTMLElement, binding: any) {
        el._clickOutside = (event: Event) => {
          if (!el.contains(event.target as Node)) {
            binding.value()
          }
        }
        document.addEventListener('click', el._clickOutside)
      },
      unmounted(el: HTMLElement) {
        document.removeEventListener('click', el._clickOutside)
      }
    }
  }
}
</script>
