<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import NavIsland from '@/components/NavIsland.vue'
import Sidebar from '@/components/Sidebar.vue'

interface AuditEvent {
  id: string
  event_type: string
  agent_id?: string
  agent_name?: string
  user_id?: string
  username?: string
  metadata?: any
  created_at: string
}

const events = ref<AuditEvent[]>([])
const total = ref(0)
const loading = ref(true)
const limit = ref(50)
const offset = ref(0)
const expandedId = ref<string | null>(null)
const autoRefresh = ref(false)
let refreshTimer: ReturnType<typeof setInterval> | null = null

// Filters
const filterEventType = ref('')
const filterAgent = ref('')
const filterDateFrom = ref('')
const filterDateTo = ref('')
const eventTypes = ref<string[]>([])
const stats = ref<Record<string, any>>({})

const totalPages = computed(() => Math.ceil(total.value / limit.value))
const currentPage = computed(() => Math.floor(offset.value / limit.value) + 1)

onMounted(async () => {
  await Promise.all([loadTypes(), loadStats(), loadEvents()])
})

onMounted(() => {
  // Watch auto-refresh
  import('vue').then(({ watch }) => {
    watch(autoRefresh, (val) => {
      if (val) {
        refreshTimer = setInterval(loadEvents, 15000)
      } else {
        if (refreshTimer) clearInterval(refreshTimer)
        refreshTimer = null
      }
    })
  })
})

async function loadTypes() {
  try {
    const res = await fetch('/api/audit-log/types')
    const data = await res.json()
    eventTypes.value = data.event_types || []
  } catch { /* ignore */ }
}

async function loadStats() {
  try {
    const res = await fetch('/api/audit-log/stats')
    stats.value = await res.json()
  } catch { /* ignore */ }
}

function buildQueryString(): string {
  const params = new URLSearchParams()
  if (filterEventType.value) params.set('event_type', filterEventType.value)
  if (filterAgent.value) params.set('agent_id', filterAgent.value)
  if (filterDateFrom.value) params.set('date_from', filterDateFrom.value + 'T00:00:00')
  if (filterDateTo.value) params.set('date_to', filterDateTo.value + 'T23:59:59')
  params.set('limit', String(limit.value))
  params.set('offset', String(offset.value))
  return params.toString()
}

async function loadEvents() {
  loading.value = true
  try {
    const res = await fetch(`/api/audit-log?${buildQueryString()}`)
    const data = await res.json()
    events.value = data.events || []
    total.value = data.total || 0
  } catch (e) {
    console.error('Failed to load audit events:', e)
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  offset.value = 0
  loadEvents()
}

function nextPage() {
  if (offset.value + limit.value < total.value) {
    offset.value += limit.value
    loadEvents()
  }
}

function prevPage() {
  if (offset.value >= limit.value) {
    offset.value -= limit.value
    loadEvents()
  }
}

function toggleExpand(id: string) {
  expandedId.value = expandedId.value === id ? null : id
}

function formatTimestamp(iso: string): string {
  try {
    const d = new Date(iso)
    return d.toLocaleString()
  } catch {
    return iso
  }
}

function formatRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

function eventBadgeClass(type: string): string {
  if (type.includes('created') || type.includes('started')) return 'badge-success'
  if (type.includes('deleted') || type.includes('ended')) return 'badge-dim'
  if (type.includes('updated') || type.includes('changed')) return 'badge-info'
  if (type.includes('credential') || type.includes('queue')) return 'badge-warn'
  return 'badge-default'
}

function eventDescription(e: AuditEvent): string {
  if (!e.metadata) return e.event_type
  const m = e.metadata
  if (e.event_type === 'agent_created') return `Created agent "${e.agent_name || m.name}"`
  if (e.event_type === 'agent_updated') return `Updated agent "${e.agent_name}" — ${(m.fields_changed || []).join(', ')}`
  if (e.event_type === 'agent_deleted') return `Deleted agent "${e.agent_name || m.name}"`
  if (e.event_type === 'session_started') return `Session started for "${e.agent_name}"`
  if (e.event_type === 'session_ended') return `Session ended for "${e.agent_name}" — ${m.turns || 0} turns`
  if (e.event_type === 'credential_set') return `Set credential "${m.credential_name}" for "${e.agent_name}"`
  if (e.event_type === 'credential_deleted') return `Deleted credential "${m.credential_name}" from "${e.agent_name}"`
  if (e.event_type === 'queue_resolved') return `Queue item resolved: ${m.resolution || ''}`
  if (e.event_type === 'settings_changed') return `Settings changed: ${(m.fields_changed || []).join(', ')}`
  return e.event_type
}

async function exportCsv() {
  const params = new URLSearchParams()
  if (filterEventType.value) params.set('event_type', filterEventType.value)
  if (filterAgent.value) params.set('agent_id', filterAgent.value)
  if (filterDateFrom.value) params.set('date_from', filterDateFrom.value + 'T00:00:00')
  if (filterDateTo.value) params.set('date_to', filterDateTo.value + 'T23:59:59')
  window.open(`/api/audit-log/export?${params.toString()}`, '_blank')
}
</script>

<template>
  <NavIsland />
  <div class="audit-page">
    <Sidebar />
    <main class="main">
      <!-- Header -->
      <div class="audit-header fade-up">
        <div class="audit-title">
          <h1>Audit Log</h1>
          <p>Complete event trail across all slices</p>
        </div>
      </div>

      <!-- Stats bar -->
      <div class="stats-row fade-up fade-up-d2">
        <div class="stat-card">
          <span class="stat-value">{{ stats.total || 0 }}</span>
          <span class="stat-label">30-day events</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{{ Object.keys(stats.event_types || {}).length }}</span>
          <span class="stat-label">Event types</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{{ total }}</span>
          <span class="stat-label">Filtered total</span>
        </div>
      </div>

      <!-- Event type breakdown -->
      <div v-if="stats.event_types && Object.keys(stats.event_types).length > 0" class="stats-detail fade-up fade-up-d3">
        <span v-for="(count, type) in stats.event_types" :key="type" class="stat-chip">
          <span class="stat-chip-dot" :class="eventBadgeClass(type)"></span>
          <span class="stat-chip-name">{{ type.replace(/_/g, ' ') }}</span>
          <span class="stat-chip-count">{{ count }}</span>
        </span>
      </div>

      <!-- Filters -->
      <div class="filter-bar fade-up fade-up-d4">
        <select v-model="filterEventType" class="filter-select">
          <option value="">All event types</option>
          <option v-for="t in eventTypes" :key="t" :value="t">{{ t.replace(/_/g, ' ') }}</option>
        </select>
        <input v-model="filterAgent" class="filter-input" placeholder="Agent name or ID..." />
        <input v-model="filterDateFrom" type="date" class="filter-date" />
        <input v-model="filterDateTo" type="date" class="filter-date" />
        <button class="filter-btn" @click="applyFilters">Apply</button>
        <button class="filter-btn export-btn" @click="exportCsv">Export CSV</button>
        <label class="auto-refresh-toggle">
          <input type="checkbox" v-model="autoRefresh" />
          <span>Auto (15s)</span>
        </label>
      </div>

      <!-- Results -->
      <div v-if="loading" class="loading-state fade-up fade-up-d5">
        <div class="spinner"></div>
      </div>

      <div v-else-if="events.length === 0" class="empty-state fade-up fade-up-d5">
        <div class="empty-icon">📋</div>
        <div class="empty-title">No events match your filters</div>
        <div class="empty-sub">Try broadening your search or clearing filters</div>
      </div>

      <div v-else class="results fade-up fade-up-d5">
        <!-- Pagination -->
        <div class="pagination-bar">
          <span class="page-info">{{ total }} events &middot; Page {{ currentPage }} of {{ totalPages }}</span>
          <div class="page-actions">
            <button class="page-btn" :disabled="offset === 0" @click="prevPage">← Previous</button>
            <button class="page-btn" :disabled="offset + limit >= total" @click="nextPage">Next →</button>
          </div>
        </div>

        <!-- Event rows -->
        <div v-for="e in events" :key="e.id" class="event-row" @click="toggleExpand(e.id)">
          <div class="event-main">
            <span class="event-time" :title="formatTimestamp(e.created_at)">{{ formatRelative(e.created_at) }}</span>
            <span class="event-badge" :class="eventBadgeClass(e.event_type)">{{ e.event_type.replace(/_/g, ' ') }}</span>
            <span class="event-agent" v-if="e.agent_name">{{ e.agent_name }}</span>
            <span class="event-user" v-if="e.username">{{ e.username }}</span>
            <span class="event-desc">{{ eventDescription(e) }}</span>
            <span class="expand-icon">{{ expandedId === e.id ? '▲' : '▼' }}</span>
          </div>
          <!-- Expanded metadata -->
          <div v-if="expandedId === e.id" class="event-detail">
            <div class="meta-row"><span class="meta-label">ID</span><span class="meta-val">{{ e.id }}</span></div>
            <div class="meta-row"><span class="meta-label">Type</span><span class="meta-val">{{ e.event_type }}</span></div>
            <div class="meta-row" v-if="e.agent_name"><span class="meta-label">Agent</span><span class="meta-val">{{ e.agent_name }} ({{ e.agent_id }})</span></div>
            <div class="meta-row" v-if="e.username"><span class="meta-label">User</span><span class="meta-val">{{ e.username }}</span></div>
            <div class="meta-row"><span class="meta-label">When</span><span class="meta-val">{{ formatTimestamp(e.created_at) }}</span></div>
            <div class="meta-row" v-if="e.metadata">
              <span class="meta-label">Metadata</span>
              <pre class="meta-pre">{{ JSON.stringify(e.metadata, null, 2) }}</pre>
            </div>
          </div>
        </div>

        <!-- Bottom pagination -->
        <div class="pagination-bar">
          <span class="page-info">{{ total }} events &middot; Page {{ currentPage }} of {{ totalPages }}</span>
          <div class="page-actions">
            <button class="page-btn" :disabled="offset === 0" @click="prevPage">← Previous</button>
            <button class="page-btn" :disabled="offset + limit >= total" @click="nextPage">Next →</button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.audit-page {
  display: flex;
  gap: 0;
  padding: 24px 32px 32px;
  margin-top: 8px;
  max-width: 1440px;
  margin-left: auto;
  margin-right: auto;
}
.main {
  flex: 1;
  min-width: 0;
}
.audit-header {
  margin-bottom: 20px;
}
.audit-title h1 {
  font-family: 'Clash Display', sans-serif;
  font-size: 26px;
  font-weight: 600;
  letter-spacing: -0.03em;
  color: #F0F0F2;
}
.audit-title p {
  font-size: 13px;
  color: rgba(255,255,255,0.3);
  font-weight: 500;
  margin-top: 2px;
}

.stats-row {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
.stat-card {
  flex: 1;
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.04);
  border-radius: 12px;
  padding: 14px 18px;
}
.stat-value {
  display: block;
  font-size: 28px;
  font-weight: 600;
  color: #F0F0F2;
  letter-spacing: -0.02em;
}
.stat-label {
  display: block;
  font-size: 11px;
  color: rgba(255,255,255,0.35);
  font-weight: 500;
  margin-top: 2px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.stats-detail {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 16px;
}
.stat-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 8px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.04);
  font-size: 11px;
}
.stat-chip-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
.stat-chip-name {
  color: rgba(255,255,255,0.6);
}
.stat-chip-count {
  color: rgba(255,255,255,0.35);
  font-weight: 600;
  margin-left: 2px;
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.filter-select, .filter-input, .filter-date {
  background: transparent;
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  border: 1px solid rgba(233,236,224,0.15);
  border-radius: 8px;
  padding: 6px 10px;
  font-size: 12px;
  color: rgba(233,236,224,0.7);
  font-family: inherit;
  outline: none;
}
.filter-select:focus, .filter-input:focus, .filter-date:focus {
  border-color: #9DD522;
}
.filter-input {
  width: 160px;
}
.filter-date {
  width: 140px;
  color-scheme: dark;
}

.filter-btn {
  display: inline-flex;
  align-items: center;
  padding: 6px 14px;
  border-radius: 8px;
  border: none;
  background: rgba(157,213,34,0.12);
  color: #9DD522;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}
.filter-btn:hover {
  background: rgba(157,213,34,0.2);
}
.export-btn {
  background: rgba(233,236,224,0.04);
  color: rgba(233,236,224,0.5);
}
.export-btn:hover {
  background: rgba(233,236,224,0.08);
  color: rgba(233,236,224,0.7);
}

.auto-refresh-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: rgba(255,255,255,0.35);
  cursor: pointer;
  margin-left: auto;
}
.auto-refresh-toggle input {
  accent-color: #9DD522;
}

.loading-state {
  display: flex;
  justify-content: center;
  padding: 60px 0;
}
.spinner {
  width: 28px;
  height: 28px;
  border: 2px solid rgba(255,255,255,0.06);
  border-top-color: #9DD522;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.empty-state {
  text-align: center;
  padding: 60px 0;
}
.empty-icon {
  font-size: 36px;
  margin-bottom: 12px;
  opacity: 0.4;
}
.empty-title {
  font-size: 15px;
  font-weight: 500;
  color: rgba(255,255,255,0.5);
}
.empty-sub {
  font-size: 12px;
  color: rgba(255,255,255,0.25);
  margin-top: 4px;
}

.pagination-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
  margin-bottom: 4px;
}
.page-info {
  font-size: 11px;
  color: rgba(255,255,255,0.3);
}
.page-actions {
  display: flex;
  gap: 6px;
}
.page-btn {
  padding: 4px 12px;
  border-radius: 6px;
  border: 1px solid rgba(255,255,255,0.06);
  background: rgba(255,255,255,0.03);
  color: rgba(255,255,255,0.5);
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}
.page-btn:hover:not(:disabled) {
  background: rgba(255,255,255,0.06);
  color: rgba(255,255,255,0.7);
}
.page-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.event-row {
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.04);
  border-radius: 10px;
  margin-bottom: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.event-row:hover {
  background: rgba(255,255,255,0.04);
  border-color: rgba(255,255,255,0.08);
}

.event-main {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  font-size: 12px;
}
.event-time {
  color: rgba(255,255,255,0.3);
  font-size: 11px;
  white-space: nowrap;
  min-width: 60px;
}
.event-badge {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
  text-transform: lowercase;
  white-space: nowrap;
  letter-spacing: 0.02em;
}
.badge-success {
  background: rgba(34,197,94,0.1);
  color: #22C55E;
}
.badge-dim {
  background: rgba(255,255,255,0.04);
  color: rgba(255,255,255,0.35);
}
.badge-info {
  background: rgba(157,213,34,0.1);
  color: #9DD522;
}
.badge-warn {
  background: rgba(245,158,11,0.1);
  color: #F59E0B;
}
.badge-default {
  background: rgba(255,255,255,0.04);
  color: rgba(255,255,255,0.5);
}

.event-agent {
  color: rgba(255,255,255,0.5);
  font-weight: 500;
  white-space: nowrap;
}
.event-user {
  color: rgba(255,255,255,0.35);
  font-size: 11px;
  white-space: nowrap;
}
.event-desc {
  flex: 1;
  color: rgba(255,255,255,0.6);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.expand-icon {
  color: rgba(255,255,255,0.2);
  font-size: 10px;
  margin-left: auto;
}

.event-detail {
  padding: 0 14px 12px;
  border-top: 1px solid rgba(255,255,255,0.03);
  padding-top: 10px;
}
.meta-row {
  display: flex;
  gap: 8px;
  font-size: 11px;
  padding: 3px 0;
}
.meta-label {
  color: rgba(255,255,255,0.3);
  min-width: 70px;
  flex-shrink: 0;
}
.meta-val {
  color: rgba(255,255,255,0.6);
  word-break: break-all;
}
.meta-pre {
  font-family: 'JetBrains Mono', Menlo, monospace;
  font-size: 10px;
  color: rgba(255,255,255,0.5);
  background: rgba(255,255,255,0.02);
  padding: 8px;
  border-radius: 6px;
  overflow-x: auto;
  max-height: 200px;
  white-space: pre-wrap;
  word-break: break-all;
  flex: 1;
}

.fade-up {
  opacity: 0;
  transform: translateY(16px);
  animation: fadeUp 0.7s cubic-bezier(0.32,0.72,0,1) forwards;
}
.fade-up-d2 { animation-delay: 0.05s; }
.fade-up-d3 { animation-delay: 0.1s; }
.fade-up-d4 { animation-delay: 0.15s; }
.fade-up-d5 { animation-delay: 0.2s; }
@keyframes fadeUp { to { opacity: 1; transform: translateY(0); } }

@media (max-width: 968px) {
  .audit-page { padding: 16px; flex-direction: column; }
  .stats-row { flex-direction: column; }
  .filter-bar { flex-direction: column; align-items: stretch; }
  .filter-input, .filter-date { width: 100%; }
  .event-main { flex-wrap: wrap; }
}
</style>
