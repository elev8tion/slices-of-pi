<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { toastBus } from '@/main'

const props = defineProps<{ agentId: string }>()

const auth = useAuthStore()

interface Share {
  agent_id: string
  user_id: string
  permission: string
  shared_at: string
  username: string
  email: string
  user_role: string
}

interface AccessRequest {
  id: string
  agent_id: string
  requester_email: string
  message: string | null
  status: string
  created_at: string
}

const shares = ref<Share[]>([])
const requests = ref<AccessRequest[]>([])
const loading = ref(false)
const shareEmail = ref('')
const sharePermission = ref('chat')
const sharing = ref(false)

const activeTab = ref<'shares' | 'requests'>('shares')

onMounted(() => {
  loadShares()
  loadRequests()
})

async function loadShares() {
  loading.value = true
  try {
    const res = await fetch(`/api/agents/${props.agentId}/shares`, {
      headers: auth.authHeaders(),
    })
    if (res.ok) {
      shares.value = await res.json()
    }
  } catch {
    // silent
  } finally {
    loading.value = false
  }
}

async function loadRequests() {
  try {
    const res = await fetch(`/api/agents/${props.agentId}/access-requests`, {
      headers: auth.authHeaders(),
    })
    if (res.ok) {
      requests.value = await res.json()
    }
  } catch {
    // silent
  }
}

async function addShare() {
  if (!shareEmail.value.trim()) return
  sharing.value = true
  try {
    const res = await fetch(`/api/agents/${props.agentId}/shares`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...auth.authHeaders() },
      body: JSON.stringify({ email: shareEmail.value.trim(), permission: sharePermission.value }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to share' }))
      toastBus.error(err.detail || 'Failed to share')
      return
    }
    toastBus.success(`Shared with ${shareEmail.value.trim()}`)
    shareEmail.value = ''
    await loadShares()
  } finally {
    sharing.value = false
  }
}

async function removeShare(userId: string, email: string) {
  if (!confirm(`Remove access for ${email}?`)) return
  try {
    const res = await fetch(`/api/agents/${props.agentId}/shares/${userId}`, {
      method: 'DELETE',
      headers: auth.authHeaders(),
    })
    if (res.ok) {
      toastBus.success(`Access revoked for ${email}`)
      await loadShares()
    }
  } catch {
    // silent
  }
}

async function resolveRequest(reqId: string, action: 'approve' | 'reject') {
  try {
    const res = await fetch(`/api/agents/${props.agentId}/access-requests/${reqId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', ...auth.authHeaders() },
      body: JSON.stringify({ action }),
    })
    if (res.ok) {
      toastBus.success(action === 'approve' ? 'Request approved' : 'Request rejected')
      await loadRequests()
      await loadShares()
    }
  } catch {
    // silent
  }
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  return `${Math.floor(mins / 60)}h ago`
}
</script>

<template>
  <div class="sharing-panel">
    <!-- Tabs -->
    <div class="sharing-tabs">
      <button
        class="sharing-tab"
        :class="{ active: activeTab === 'shares' }"
        @click="activeTab = 'shares'"
      >
        Shared Users
        <span v-if="shares.length" class="sharing-badge">{{ shares.length }}</span>
      </button>
      <button
        class="sharing-tab"
        :class="{ active: activeTab === 'requests' }"
        @click="activeTab = 'requests'"
      >
        Access Requests
        <span v-if="requests.length" class="sharing-badge">{{ requests.length }}</span>
      </button>
    </div>

    <!-- Shares Tab -->
    <div v-if="activeTab === 'shares'">
      <!-- Add share form -->
      <div class="share-form">
        <input
          v-model="shareEmail"
          type="email"
          placeholder="user@example.com"
          class="share-input"
        />
        <select v-model="sharePermission" class="share-select">
          <option value="chat">Chat</option>
          <option value="admin">Admin</option>
        </select>
        <button
          class="share-btn"
          :disabled="!shareEmail.trim() || sharing"
          @click="addShare"
        >
          {{ sharing ? '...' : 'Share' }}
        </button>
      </div>

      <!-- Shares list -->
      <div v-if="loading" class="text-xs text-text-tertiary text-center py-4">Loading...</div>
      <div v-else-if="shares.length === 0" class="text-xs text-text-tertiary text-center py-4">
        No users have been granted access yet.
      </div>
      <div v-else class="shares-list">
        <div v-for="s in shares" :key="s.user_id" class="share-row">
          <div class="share-user">
            <div class="share-avatar">{{ s.username[0].toUpperCase() }}</div>
            <div>
              <div class="share-name">{{ s.username }}</div>
              <div class="share-email">{{ s.email }}</div>
            </div>
          </div>
          <div class="share-meta">
            <span class="share-permission" :class="'perm-' + s.permission">
              {{ s.permission }}
            </span>
            <span class="share-time">{{ timeAgo(s.shared_at) }}</span>
            <button class="share-remove" @click="removeShare(s.user_id, s.email)" title="Remove access">✕</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Requests Tab -->
    <div v-if="activeTab === 'requests'">
      <div v-if="requests.length === 0" class="text-xs text-text-tertiary text-center py-4">
        No pending access requests.
      </div>
      <div v-else class="requests-list">
        <div v-for="r in requests" :key="r.id" class="request-row">
          <div>
            <div class="request-email">{{ r.requester_email }}</div>
            <div v-if="r.message" class="request-message">{{ r.message }}</div>
            <div class="request-status" :class="'status-' + r.status">{{ r.status }}</div>
          </div>
          <div v-if="r.status === 'pending'" class="request-actions">
            <button class="request-approve" @click="resolveRequest(r.id, 'approve')">Approve</button>
            <button class="request-reject" @click="resolveRequest(r.id, 'reject')">Reject</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sharing-panel {
  padding: 16px;
}
.sharing-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 16px;
  border-bottom: 1px solid rgba(255,255,255,0.04);
}
.sharing-tab {
  padding: 8px 14px;
  font-size: 12px;
  font-weight: 500;
  color: rgba(255,255,255,0.3);
  background: none;
  border: none;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
}
.sharing-tab:hover {
  color: rgba(255,255,255,0.5);
}
.sharing-tab.active {
  color: rgba(255,255,255,0.85);
  border-bottom-color: #9DD522;
}
.sharing-badge {
  background: rgba(157,213,34,0.12);
  color: #9DD522;
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 9999px;
}

.share-form {
  display: flex;
  gap: 6px;
  margin-bottom: 16px;
}
.share-input {
  flex: 1;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  padding: 7px 10px;
  font-size: 12px;
  color: #F0F0F2;
  font-family: inherit;
  outline: none;
}
.share-input:focus {
  border-color: rgba(157,213,34,0.4);
}
.share-input::placeholder {
  color: rgba(255,255,255,0.15);
}
.share-select {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  padding: 7px 8px;
  font-size: 11px;
  color: rgba(255,255,255,0.7);
  font-family: inherit;
  outline: none;
  cursor: pointer;
}
.share-btn {
  background: #9DD522;
  color: #0A0A0A;
  border: none;
  border-radius: 8px;
  padding: 7px 14px;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}
.share-btn:hover:not(:disabled) {
  background: #8BC01E;
}
.share-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.shares-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.share-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  border-radius: 8px;
  transition: background 0.2s;
}
.share-row:hover {
  background: rgba(255,255,255,0.02);
}
.share-user {
  display: flex;
  align-items: center;
  gap: 8px;
}
.share-avatar {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: rgba(157,213,34,0.15);
  color: #9DD522;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
}
.share-name {
  font-size: 13px;
  font-weight: 500;
  color: rgba(255,255,255,0.8);
}
.share-email {
  font-size: 11px;
  color: rgba(255,255,255,0.3);
}
.share-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}
.share-permission {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 9999px;
  text-transform: uppercase;
}
.perm-chat {
  background: rgba(157,213,34,0.1);
  color: #9DD522;
}
.perm-admin {
  background: rgba(245,158,11,0.1);
  color: #F59E0B;
}
.share-time {
  font-size: 10px;
  color: rgba(255,255,255,0.2);
}
.share-remove {
  background: none;
  border: none;
  color: rgba(255,255,255,0.2);
  font-size: 12px;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
}
.share-remove:hover {
  color: #EF4444;
  background: rgba(239,68,68,0.1);
}

.requests-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.request-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px;
  border-radius: 8px;
  background: rgba(255,255,255,0.02);
}
.request-email {
  font-size: 12px;
  font-weight: 500;
  color: rgba(255,255,255,0.7);
}
.request-message {
  font-size: 11px;
  color: rgba(255,255,255,0.35);
  margin-top: 2px;
}
.request-status {
  font-size: 10px;
  font-weight: 600;
  margin-top: 4px;
  text-transform: uppercase;
}
.status-pending {
  color: #F59E0B;
}
.status-approved {
  color: #22C55E;
}
.status-rejected {
  color: #EF4444;
}
.request-actions {
  display: flex;
  gap: 6px;
}
.request-approve {
  background: rgba(34,197,94,0.1);
  color: #22C55E;
  border: 1px solid rgba(34,197,94,0.2);
  border-radius: 6px;
  padding: 4px 10px;
  font-size: 10px;
  font-weight: 600;
  cursor: pointer;
}
.request-approve:hover {
  background: rgba(34,197,94,0.2);
}
.request-reject {
  background: rgba(239,68,68,0.1);
  color: #EF4444;
  border: 1px solid rgba(239,68,68,0.2);
  border-radius: 6px;
  padding: 4px 10px;
  font-size: 10px;
  font-weight: 600;
  cursor: pointer;
}
.request-reject:hover {
  background: rgba(239,68,68,0.2);
}
</style>
