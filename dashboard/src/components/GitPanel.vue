<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { toastBus } from '@/main'

const props = defineProps<{ agentId: string }>()

const loading = ref(true)
const operating = ref<'commit' | 'push' | 'pull' | 'init' | null>(null)
const commitMsg = ref('')
const expandedCommit = ref<string | null>(null)
const commitDiff = ref('')
const diffLoading = ref(false)

// Init form
const showInitForm = ref(false)
const initRepoUrl = ref('')
const initLoading = ref(false)

const gitStatus = ref<any>(null)
const commitLog = ref<any[]>([])
const autoRefresh = ref(true)
let refreshTimer: ReturnType<typeof setInterval> | null = null

const hasChanges = computed(() => {
  if (!gitStatus.value?.enabled) return false
  const s = gitStatus.value
  return (s.modified?.length || 0) + (s.staged?.length || 0) + (s.untracked?.length || 0) > 0
})

const statusChangedFiles = computed(() => {
  if (!gitStatus.value?.enabled) return []
  const s = gitStatus.value
  const files: { path: string; type: string }[] = []
  for (const f of s.staged || []) files.push({ path: f, type: 'staged' })
  for (const f of s.modified || []) files.push({ path: f, type: 'modified' })
  for (const f of s.untracked || []) files.push({ path: f, type: 'untracked' })
  return files
})

async function refresh() {
  loading.value = true
  try {
    const [statusRes, logRes] = await Promise.all([
      fetch(`/api/agents/${props.agentId}/git/status`),
      fetch(`/api/agents/${props.agentId}/git/log?limit=20`),
    ])
    if (statusRes.ok) gitStatus.value = await statusRes.json()
    if (logRes.ok) {
      const data = await logRes.json()
      commitLog.value = data.commits || []
    }
  } catch (e) {
    console.error('Git refresh failed:', e)
  } finally {
    loading.value = false
  }
}

async function initRepo() {
  initLoading.value = true
  operating.value = 'init'
  try {
    const body: any = {}
    if (initRepoUrl.value.trim()) body.repo_url = initRepoUrl.value.trim()
    const res = await fetch(`/api/agents/${props.agentId}/git/init`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    const result = await res.json()
    if (res.ok && result.status === 'initialized') {
      toastBus.success('Git repository initialized')
      showInitForm.value = false
      await refresh()
    } else {
      toastBus.error(result.error || 'Init failed')
    }
  } catch (e: any) {
    toastBus.error(e.message || 'Init failed')
  } finally {
    initLoading.value = false
    operating.value = null
  }
}

async function commit() {
  if (!commitMsg.value.trim()) return
  operating.value = 'commit'
  try {
    const res = await fetch(`/api/agents/${props.agentId}/git/commit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: commitMsg.value.trim() }),
    })
    const result = await res.json()
    if (res.ok && result.status === 'committed') {
      toastBus.success(`Committed: ${commitMsg.value.trim().slice(0, 50)}`)
      commitMsg.value = ''
      await refresh()
    } else {
      toastBus.error(result.error || 'Commit failed')
    }
  } catch (e: any) {
    toastBus.error(e.message || 'Commit failed')
  } finally {
    operating.value = null
  }
}

async function push() {
  operating.value = 'push'
  try {
    const res = await fetch(`/api/agents/${props.agentId}/git/push`, { method: 'POST' })
    const result = await res.json()
    if (res.ok) {
      toastBus.success('Pushed to remote')
      await refresh()
    } else {
      toastBus.error(result.error || 'Push failed')
    }
  } catch (e: any) {
    toastBus.error(e.message || 'Push failed')
  } finally {
    operating.value = null
  }
}

async function pull() {
  operating.value = 'pull'
  try {
    const res = await fetch(`/api/agents/${props.agentId}/git/pull`, { method: 'POST' })
    const result = await res.json()
    if (res.ok) {
      toastBus.success('Pulled from remote')
      await refresh()
    } else {
      toastBus.error(result.error || 'Pull failed')
    }
  } catch (e: any) {
    toastBus.error(e.message || 'Pull failed')
  } finally {
    operating.value = null
  }
}

async function toggleDiff(hash: string) {
  if (expandedCommit.value === hash) {
    expandedCommit.value = null
    commitDiff.value = ''
    return
  }
  expandedCommit.value = hash
  diffLoading.value = true
  commitDiff.value = ''
  try {
    const res = await fetch(`/api/agents/${props.agentId}/git/diff?hash=${encodeURIComponent(hash)}`)
    if (res.ok) {
      const data = await res.json()
      commitDiff.value = data.diff || data.error || ''
    }
  } catch {
    commitDiff.value = 'Failed to load diff'
  } finally {
    diffLoading.value = false
  }
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

onMounted(() => {
  refresh()
  if (autoRefresh.value) {
    refreshTimer = setInterval(refresh, 15000)
  }
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<template>
  <div class="git-panel">
    <!-- Not initialized -->
    <div v-if="!loading && (!gitStatus || !gitStatus.enabled)" class="git-empty">
      <div class="text-3xl mb-3 opacity-30">〈〉</div>
      <div class="git-empty-title">No Git Repository</div>
      <div class="git-empty-sub">Initialize a git repo to version-control this agent's configs.</div>

      <div v-if="!showInitForm" class="mt-4">
        <button class="btn-primary" @click="showInitForm = true">Initialize Repo</button>
      </div>

      <form v-else @submit.prevent="initRepo" class="git-init-form mt-4">
        <input
          v-model="initRepoUrl"
          type="text"
          class="git-input"
          placeholder="GitHub repo URL (optional)"
          :disabled="initLoading"
        />
        <div class="flex gap-2 mt-2 justify-center">
          <button type="submit" class="btn-primary" :disabled="initLoading">
            {{ initLoading ? 'Initializing...' : 'Initialize' }}
          </button>
          <button type="button" class="btn-ghost" @click="showInitForm = false">Cancel</button>
        </div>
      </form>
    </div>

    <!-- Git Status + Actions -->
    <template v-else-if="gitStatus?.enabled">
      <!-- Status bar -->
      <div class="git-status-bar">
        <div class="flex items-center gap-3">
          <span class="git-branch">⎇ {{ gitStatus.branch }}</span>
          <span v-if="gitStatus.ahead > 0" class="git-count-ahead">↑{{ gitStatus.ahead }}</span>
          <span v-if="gitStatus.behind > 0" class="git-count-behind">↓{{ gitStatus.behind }}</span>
          <span class="git-file-count">{{ statusChangedFiles.length }} changed</span>
        </div>
        <div class="flex items-center gap-1.5">
          <button class="git-btn" title="Refresh" @click="refresh" :disabled="loading">⟳</button>
        </div>
      </div>

      <!-- Changed files -->
      <div v-if="statusChangedFiles.length > 0" class="git-section">
        <div class="git-section-title">Changed Files</div>
        <div class="git-file-list">
          <div v-for="file in statusChangedFiles" :key="file.path" class="git-file-row">
            <span class="git-file-status" :class="'status-' + file.type">{{ file.type[0] }}</span>
            <span class="git-file-path">{{ file.path }}</span>
          </div>
        </div>

        <!-- Commit form -->
        <form @submit.prevent="commit" class="git-commit-form">
          <input
            v-model="commitMsg"
            type="text"
            class="git-input"
            placeholder="Commit message..."
            :disabled="operating === 'commit'"
          />
          <div class="flex gap-1.5">
            <button type="submit" class="git-btn btn-primary" :disabled="!commitMsg.trim() || operating === 'commit'">
              {{ operating === 'commit' ? '...' : 'Commit' }}
            </button>
            <button type="button" class="git-btn" :disabled="!gitStatus.has_remote || operating === 'push'" @click="push">
              {{ operating === 'push' ? '...' : 'Push' }}
            </button>
            <button type="button" class="git-btn" :disabled="!gitStatus.has_remote || operating === 'pull'" @click="pull">
              {{ operating === 'pull' ? '...' : 'Pull' }}
            </button>
          </div>
        </form>
      </div>

      <div v-else class="git-clean">
        <span class="text-success">✔</span> Working tree clean
        <button v-if="gitStatus.has_remote" type="button" class="git-btn ml-3" :disabled="operating === 'pull'" @click="pull">
          Pull
        </button>
      </div>

      <!-- Commit history -->
      <div class="git-section">
        <div class="git-section-title">History</div>
        <div v-if="commitLog.length === 0" class="git-empty-sub text-center py-4">
          No commits yet
        </div>
        <div v-else class="git-commit-list">
          <div
            v-for="c in commitLog"
            :key="c.hash"
            class="git-commit-row"
            :class="{ expanded: expandedCommit === c.hash }"
            @click="toggleDiff(c.hash)"
          >
            <div class="git-commit-header">
              <span class="git-commit-hash">{{ c.hash }}</span>
              <span class="git-commit-msg">{{ c.message }}</span>
              <span class="git-commit-meta">
                {{ c.author }} · {{ timeAgo(c.date) }}
              </span>
            </div>
            <div v-if="expandedCommit === c.hash" class="git-diff">
              <pre v-if="diffLoading" class="git-diff-text">Loading diff...</pre>
              <pre v-else class="git-diff-text" v-text="commitDiff || '(binary or empty commit)'"></pre>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- Loading -->
    <div v-else class="git-empty">
      <div class="text-sm text-text-tertiary">Loading git status...</div>
    </div>
  </div>
</template>

<style scoped>
.git-panel {
  padding: 16px;
  font-size: 13px;
}
.git-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  color: rgba(255,255,255,0.3);
  text-align: center;
}
.git-empty-title {
  font-size: 16px;
  font-weight: 600;
  color: rgba(255,255,255,0.5);
  margin-bottom: 6px;
}
.git-empty-sub {
  font-size: 12px;
  color: rgba(255,255,255,0.25);
}
.git-status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.04);
  border-radius: 10px;
  margin-bottom: 12px;
}
.git-branch {
  font-weight: 600;
  color: #9DD522;
  font-size: 12px;
}
.git-count-ahead {
  color: #22C55E;
  font-size: 11px;
  font-weight: 500;
}
.git-count-behind {
  color: #F59E0B;
  font-size: 11px;
  font-weight: 500;
}
.git-file-count {
  font-size: 11px;
  color: rgba(255,255,255,0.3);
}
.git-section {
  margin-bottom: 16px;
}
.git-section-title {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: rgba(255,255,255,0.3);
  margin-bottom: 8px;
}
.git-file-list {
  border: 1px solid rgba(255,255,255,0.04);
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 8px;
}
.git-file-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  font-size: 12px;
  border-bottom: 1px solid rgba(255,255,255,0.02);
}
.git-file-row:last-child {
  border-bottom: none;
}
.git-file-status {
  width: 18px;
  height: 18px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
  flex-shrink: 0;
}
.status-staged {
  background: rgba(34,197,94,0.15);
  color: #22C55E;
}
.status-modified {
  background: rgba(245,158,11,0.15);
  color: #F59E0B;
}
.status-untracked {
  background: rgba(157,213,34,0.15);
  color: #9DD522;
}
.git-file-path {
  color: rgba(255,255,255,0.6);
  font-family: 'JetBrains Mono', Menlo, monospace;
  font-size: 11px;
}
.git-commit-form {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.git-input {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 12px;
  color: rgba(255,255,255,0.7);
  font-family: inherit;
  outline: none;
  width: 100%;
}
.git-input:focus {
  border-color: rgba(157,213,34,0.4);
}
.git-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 5px 10px;
  border-radius: 6px;
  border: 1px solid rgba(255,255,255,0.06);
  background: rgba(255,255,255,0.03);
  color: rgba(255,255,255,0.5);
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}
.git-btn:hover:not(:disabled) {
  background: rgba(255,255,255,0.07);
  color: rgba(255,255,255,0.8);
}
.git-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.btn-primary {
  background: rgba(157,213,34,0.15);
  border-color: rgba(157,213,34,0.2);
  color: #9DD522;
}
.btn-primary:hover:not(:disabled) {
  background: rgba(157,213,34,0.25);
}
.git-clean {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  background: rgba(34,197,94,0.04);
  border: 1px solid rgba(34,197,94,0.08);
  border-radius: 8px;
  font-size: 12px;
  color: rgba(255,255,255,0.4);
  margin-bottom: 16px;
}
.git-commit-list {
  border: 1px solid rgba(255,255,255,0.04);
  border-radius: 8px;
  overflow: hidden;
}
.git-commit-row {
  border-bottom: 1px solid rgba(255,255,255,0.02);
  cursor: pointer;
  transition: background 0.2s;
}
.git-commit-row:last-child {
  border-bottom: none;
}
.git-commit-row:hover {
  background: rgba(255,255,255,0.02);
}
.git-commit-row.expanded {
  background: rgba(157,213,34,0.04);
}
.git-commit-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
}
.git-commit-hash {
  font-family: 'JetBrains Mono', Menlo, monospace;
  font-size: 10px;
  color: #9DD522;
  flex-shrink: 0;
}
.git-commit-msg {
  flex: 1;
  font-size: 12px;
  color: rgba(255,255,255,0.6);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.git-commit-meta {
  font-size: 10px;
  color: rgba(255,255,255,0.3);
  flex-shrink: 0;
}
.git-diff {
  padding: 0 10px 8px;
}
.git-diff-text {
  font-family: 'JetBrains Mono', Menlo, monospace;
  font-size: 10px;
  line-height: 1.4;
  color: rgba(255,255,255,0.5);
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 300px;
  overflow-y: auto;
  background: rgba(0,0,0,0.2);
  border-radius: 6px;
  padding: 8px;
  margin: 0;
}

.btn-ghost {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  color: rgba(255,255,255,0.5);
  border-radius: 8px;
  padding: 8px 18px;
  font-size: 12px;
  cursor: pointer;
}
.git-init-form {
  width: 100%;
  max-width: 360px;
}
</style>
