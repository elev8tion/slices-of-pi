<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'

interface QueueItem {
  id: string
  agent_id: string
  agent_name: string
  type: string
  title: string
  description?: string
  status: string
  priority: string
  created_at: string
  updated_at?: string
  resolved_at?: string
  resolution_note?: string
}

const items = ref<QueueItem[]>([])
const loading = ref(true)
const activeFilter = ref<'all' | 'pending' | 'acknowledged' | 'resolved'>('all')
const expanded = ref<string | null>(null)
let pollTimer: ReturnType<typeof setInterval> | null = null

const filteredItems = computed(() => {
  if (activeFilter.value === 'all') return items.value
  return items.value.filter(i => i.status === activeFilter.value)
})

const pendingCount = computed(() => items.value.filter(i => i.status === 'pending').length)

async function fetchQueue() {
  try {
    const res = await fetch('/api/operator-queue')
    items.value = await res.json()
  } catch {
    // Silent
  } finally {
    loading.value = false
  }
}

async function updateStatus(item: QueueItem, status: string) {
  const note = status === 'rejected' ? prompt('Reason for rejection:') : undefined
  if (status === 'rejected' && note === null) return
  try {
    const body: any = { status }
    if (note) body.note = note
    await fetch(`/api/operator-queue/${item.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    await fetchQueue()
  } catch {
    // Silent
  }
}

async function deleteItem(item: QueueItem) {
  if (!confirm(`Remove "${item.title}"?`)) return
  try {
    await fetch(`/api/operator-queue/${item.id}`, { method: 'DELETE' })
    await fetchQueue()
  } catch {
    // Silent
  }
}

function toggleExpand(id: string) {
  expanded.value = expanded.value === id ? null : id
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

const priorityColors: Record<string, string> = {
  critical: '#EF4444',
  high: '#F59E0B',
  normal: '#9DD522',
  low: '#6B7280',
}

const typeLabels: Record<string, string> = {
  approval_needed: 'Approval',
  confirmation: 'Confirm',
  error: 'Error',
  info: 'Info',
}

const typeColors: Record<string, string> = {
  approval_needed: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  confirmation: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  error: 'bg-red-500/10 text-red-400 border-red-500/20',
  info: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
}

onMounted(() => {
  fetchQueue()
  pollTimer = setInterval(fetchQueue, 10000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div class="queue">
    <!-- Filter tabs -->
    <div class="queue-tabs">
      <button
        class="queue-tab"
        :class="{ active: activeFilter === 'all' }"
        @click="activeFilter = 'all'"
      >All ({{ items.length }})</button>
      <button
        class="queue-tab"
        :class="{ active: activeFilter === 'pending' }"
        @click="activeFilter = 'pending'"
      >
        Pending
        <span v-if="pendingCount > 0" class="queue-badge">{{ pendingCount }}</span>
      </button>
      <button
        class="queue-tab"
        :class="{ active: activeFilter === 'acknowledged' }"
        @click="activeFilter = 'acknowledged'"
      >Acknowledged</button>
      <button
        class="queue-tab"
        :class="{ active: activeFilter === 'resolved' }"
        @click="activeFilter = 'resolved'"
      >Resolved</button>
    </div>

    <!-- Items -->
    <div v-if="loading" class="queue-empty">Loading...</div>
    <div v-else-if="filteredItems.length === 0" class="queue-empty">
      <div class="text-3xl mb-2 opacity-30">✓</div>
      <div>No items needing attention</div>
    </div>
    <div v-else class="queue-list">
      <div
        v-for="item in filteredItems"
        :key="item.id"
        class="queue-card"
        :class="{ expanded: expanded === item.id }"
      >
        <div class="queue-card-header" @click="toggleExpand(item.id)">
          <!-- Priority indicator -->
          <div class="queue-priority" :style="{ background: priorityColors[item.priority] || '#9DD522' }" />

          <!-- Type badge -->
          <span
            class="queue-type-badge"
            :class="typeColors[item.type] || 'bg-white/5 text-text-tertiary border-white/8'"
          >{{ typeLabels[item.type] || item.type }}</span>

          <!-- Agent name -->
          <span class="queue-agent">{{ item.agent_name }}</span>

          <!-- Title -->
          <span class="queue-title">{{ item.title }}</span>

          <!-- Status -->
          <span class="queue-status" :class="'status-' + item.status">
            {{ item.status }}
          </span>

          <!-- Age -->
          <span class="queue-age">{{ timeAgo(item.created_at) }}</span>
        </div>

        <!-- Expanded detail -->
        <div v-if="expanded === item.id" class="queue-card-body">
          <div v-if="item.description" class="queue-desc">{{ item.description }}</div>
          <div class="queue-meta">
            <span>Priority: <strong>{{ item.priority }}</strong></span>
            <span>Type: <strong>{{ item.type }}</strong></span>
            <span>Created: <strong>{{ new Date(item.created_at).toLocaleString() }}</strong></span>
          </div>
          <div v-if="item.resolved_at" class="queue-desc">
            Resolved {{ timeAgo(item.resolved_at) }}{{ item.resolution_note ? ': ' + item.resolution_note : '' }}
          </div>

          <!-- Actions -->
          <div class="queue-actions">
            <button
              v-if="item.status === 'pending'"
              class="queue-btn queue-btn-primary"
              @click="updateStatus(item, 'acknowledged')"
            >Acknowledge</button>
            <button
              v-if="item.status === 'pending' || item.status === 'acknowledged'"
              class="queue-btn queue-btn-success"
              @click="updateStatus(item, 'resolved')"
            >Resolve</button>
            <button
              v-if="item.status === 'pending' || item.status === 'acknowledged'"
              class="queue-btn queue-btn-danger"
              @click="updateStatus(item, 'rejected')"
            >Reject</button>
            <button
              class="queue-btn queue-btn-secondary"
              @click="deleteItem(item)"
            >Remove</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.queue {
  display: flex;
  flex-direction: column;
  gap: 0;
  height: 100%;
}

.queue-tabs {
  display: flex;
  gap: 2px;
  margin-bottom: 12px;
  border-bottom: 1px solid rgba(255,255,255,0.04);
  padding-bottom: 8px;
}

.queue-tab {
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 500;
  color: rgba(255,255,255,0.3);
  background: none;
  border: none;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
}
.queue-tab:hover { color: rgba(255,255,255,0.5); background: rgba(255,255,255,0.03); }
.queue-tab.active { color: #fff; background: rgba(157,213,34,0.1); }

.queue-badge {
  background: #EF4444;
  color: #fff;
  font-size: 9px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 9999px;
  line-height: 1.3;
}

.queue-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  color: rgba(255,255,255,0.25);
  font-size: 13px;
}

.queue-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.queue-card {
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.04);
  border-radius: 10px;
  overflow: hidden;
  transition: all 0.2s;
}
.queue-card:hover {
  border-color: rgba(255,255,255,0.08);
  background: rgba(255,255,255,0.03);
}

.queue-card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  cursor: pointer;
}

.queue-priority {
  width: 3px;
  height: 24px;
  border-radius: 2px;
  flex-shrink: 0;
}

.queue-type-badge {
  font-size: 9px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 9999px;
  border: 1px solid;
  white-space: nowrap;
  flex-shrink: 0;
}

.queue-agent {
  font-size: 11px;
  font-weight: 600;
  color: rgba(255,255,255,0.5);
  white-space: nowrap;
  flex-shrink: 0;
}

.queue-title {
  flex: 1;
  font-size: 12.5px;
  font-weight: 500;
  color: rgba(255,255,255,0.8);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.queue-status {
  font-size: 9px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 9999px;
  white-space: nowrap;
  flex-shrink: 0;
}
.queue-status.status-pending {
  background: rgba(245,158,11,0.1);
  color: #F59E0B;
}
.queue-status.status-acknowledged {
  background: rgba(157,213,34,0.1);
  color: #9DD522;
}
.queue-status.status-resolved {
  background: rgba(34,197,94,0.1);
  color: #22C55E;
}
.queue-status.status-rejected {
  background: rgba(239,68,68,0.1);
  color: #EF4444;
}

.queue-age {
  font-size: 10px;
  color: rgba(255,255,255,0.2);
  white-space: nowrap;
  flex-shrink: 0;
}

.queue-card-body {
  border-top: 1px solid rgba(255,255,255,0.04);
  padding: 12px 14px 14px;
}

.queue-desc {
  font-size: 12px;
  color: rgba(255,255,255,0.5);
  line-height: 1.5;
  margin-bottom: 10px;
  white-space: pre-wrap;
}

.queue-meta {
  display: flex;
  gap: 16px;
  font-size: 10.5px;
  color: rgba(255,255,255,0.3);
  margin-bottom: 12px;
}
.queue-meta strong {
  color: rgba(255,255,255,0.6);
}

.queue-actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.queue-btn {
  padding: 5px 12px;
  border-radius: 8px;
  font-size: 10.5px;
  font-weight: 600;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
}
.queue-btn-primary {
  background: rgba(157,213,34,0.12);
  color: #9DD522;
}
.queue-btn-primary:hover { background: rgba(157,213,34,0.2); }
.queue-btn-success {
  background: rgba(34,197,94,0.12);
  color: #22C55E;
}
.queue-btn-success:hover { background: rgba(34,197,94,0.2); }
.queue-btn-danger {
  background: rgba(239,68,68,0.12);
  color: #EF4444;
}
.queue-btn-danger:hover { background: rgba(239,68,68,0.2); }
.queue-btn-secondary {
  background: rgba(233,236,224,0.04);
  color: rgba(233,236,224,0.4);
}
.queue-btn-secondary:hover { background: rgba(233,236,224,0.07); }
</style>
