<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import FilePreview from './FilePreview.vue'

const props = defineProps<{ agentId: string }>()

interface FileEntry {
  name: string
  path: string
  type: 'file' | 'dir'
  size: number
  size_formatted: string
  modified_at: string
  children?: FileEntry[]
}

const currentPath = ref('')
const entries = ref<FileEntry[]>([])
const loading = ref(false)
const error = ref('')
const selectedFile = ref<FileEntry | null>(null)
const previewContent = ref('')
const previewLoading = ref(false)
const previewTruncatedLines = ref(0)
const previewTruncatedBytes = ref(0)
const previewBase64 = ref('')
const previewMime = ref('')
const previewType = ref<'text' | 'image'>('text')
const searchQuery = ref('')
const breadcrumbs = computed(() => {
  const parts = currentPath.value.split('/').filter(Boolean)
  const crumbs = [{ label: 'Workspace', path: '' }]
  let acc = ''
  for (const p of parts) {
    acc = acc ? `${acc}/${p}` : p
    crumbs.push({ label: p, path: acc })
  }
  return crumbs
})

// Confirm dialog
const confirmAction = ref<{ message: string; onConfirm: () => void } | null>(null)

async function loadDir(dirPath: string) {
  loading.value = true
  error.value = ''
  currentPath.value = dirPath
  selectedFile.value = null
  previewContent.value = ''

  try {
    const q = dirPath ? `?path=${encodeURIComponent(dirPath)}` : ''
    const res = await fetch(`/api/agents/${props.agentId}/files${q}`)
    if (!res.ok) {
      const errText = await res.text()
      throw new Error(errText || `HTTP ${res.status}`)
    }
    const data = await res.json()
    entries.value = data.children || []
  } catch (e: any) {
    error.value = e.message || 'Failed to load directory'
    entries.value = []
  } finally {
    loading.value = false
  }
}

function navigateTo(entry: FileEntry) {
  if (entry.type === 'dir') {
    loadDir(entry.path)
  } else {
    selectFile(entry)
  }
}

function goToBreadcrumb(path: string) {
  loadDir(path)
}

async function selectFile(entry: FileEntry) {
  selectedFile.value = entry
  previewLoading.value = true

  try {
    const res = await fetch(
      `/api/agents/${props.agentId}/files/preview?path=${encodeURIComponent(entry.path)}`
    )
    if (!res.ok) throw new Error('Preview failed')
    const data = await res.json()

    if (data.type === 'image') {
      previewType.value = 'image'
      previewBase64.value = data.content
      previewMime.value = data.mime
      previewContent.value = ''
    } else {
      previewType.value = 'text'
      previewContent.value = data.content
      previewTruncatedLines.value = data.truncated_lines || 0
      previewTruncatedBytes.value = data.truncated_bytes || 0
    }
  } catch (e: any) {
    previewContent.value = `Error: ${e.message}`
    previewType.value = 'text'
  } finally {
    previewLoading.value = false
  }
}

async function downloadFile(entry: FileEntry) {
  if (entry.type === 'dir') return
  const url = `/api/agents/${props.agentId}/files/download?path=${encodeURIComponent(entry.path)}`
  window.open(url, '_blank')
}

async function uploadFile(event: Event) {
  const input = event.target as HTMLInputElement
  if (!input.files?.length) return

  const file = input.files[0]
  const formData = new FormData()
  formData.append('file', file)
  formData.append('path', currentPath.value)

  try {
    const res = await fetch(`/api/agents/${props.agentId}/files/upload`, {
      method: 'POST',
      body: formData,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(err.detail || 'Upload failed')
    }
    await loadDir(currentPath.value)
  } catch (e: any) {
    error.value = e.message
  }

  input.value = '' // Reset
}

async function createFolder() {
  const name = prompt('Folder name:')
  if (!name || !name.trim()) return

  const dirPath = currentPath.value ? `${currentPath.value}/${name.trim()}` : name.trim()
  try {
    const res = await fetch(
      `/api/agents/${props.agentId}/files/mkdir?path=${encodeURIComponent(dirPath)}`,
      { method: 'POST' }
    )
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(err.detail || 'Create failed')
    }
    await loadDir(currentPath.value)
  } catch (e: any) {
    error.value = e.message
  }
}

function confirmDelete(entry: FileEntry) {
  confirmAction.value = {
    message: `Delete "${entry.name}"?`,
    onConfirm: async () => {
      try {
        const res = await fetch(
          `/api/agents/${props.agentId}/files?path=${encodeURIComponent(entry.path)}`,
          { method: 'DELETE' }
        )
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: res.statusText }))
          throw new Error(err.detail || 'Delete failed')
        }
        if (selectedFile.value?.path === entry.path) {
          selectedFile.value = null
          previewContent.value = ''
        }
        await loadDir(currentPath.value)
      } catch (e: any) {
        error.value = e.message
      }
      confirmAction.value = null
    },
  }
}

function cancelConfirm() {
  confirmAction.value = null
}

const filteredEntries = computed(() => {
  if (!searchQuery.value) return entries.value
  const q = searchQuery.value.toLowerCase()
  return entries.value.filter(e => e.name.toLowerCase().includes(q))
})

// File/folder icons
function entryIcon(entry: FileEntry): string {
  if (entry.type === 'dir') return '📁'
  const ext = entry.name.split('.').pop()?.toLowerCase() || ''
  const iconMap: Record<string, string> = {
    py: '🐍', js: '📜', ts: '📘', vue: '💚', json: '📋', yaml: '📄',
    md: '📝', txt: '📄', html: '🌐', css: '🎨', sh: '⚡', env: '🔑',
    log: '📊', csv: '📈', png: '🖼', jpg: '🖼', jpeg: '🖼', gif: '🖼',
    svg: '🎨', pdf: '📕', zip: '📦', toml: '📄', lock: '🔒',
  }
  return iconMap[ext] || '📄'
}

onMounted(() => loadDir(''))
</script>

<template>
  <div class="file-manager">
    <!-- Toolbar -->
    <div class="fm-toolbar">
      <div class="fm-breadcrumbs">
        <button
          v-for="(crumb, i) in breadcrumbs"
          :key="i"
          class="crumb"
          :class="{ active: i === breadcrumbs.length - 1 }"
          @click="goToBreadcrumb(crumb.path)"
        >
          {{ crumb.label }}
          <span v-if="i < breadcrumbs.length - 1" class="crumb-sep">/</span>
        </button>
      </div>

      <div class="fm-actions">
        <input
          v-model="searchQuery"
          type="text"
          class="fm-search"
          placeholder="Filter files..."
        />
        <button class="fm-btn" @click="uploadFile" title="Upload file">
          <input
            type="file"
            class="fm-file-input"
            @change="uploadFile"
          />
          ⬆ Upload
        </button>
        <button class="fm-btn" @click="createFolder" title="New folder">📁 +Folder</button>
        <button class="fm-btn" @click="loadDir(currentPath)" title="Refresh">⟳</button>
      </div>
    </div>

    <!-- Error banner -->
    <div v-if="error" class="fm-error">{{ error }}</div>

    <!-- Loading -->
    <div v-if="loading" class="fm-loading">
      <span class="fm-spinner" />
      Loading...
    </div>

    <!-- Empty state -->
    <div v-else-if="filteredEntries.length === 0 && !searchQuery" class="fm-empty">
      <div class="empty-icon">📂</div>
      <div>This workspace is empty</div>
      <div class="empty-hint">Upload files or create a folder to get started</div>
    </div>

    <div v-else-if="filteredEntries.length === 0 && searchQuery" class="fm-empty">
      No files match <strong>"{{ searchQuery }}"</strong>
    </div>

    <!-- File listing + preview split -->
    <div v-else class="fm-body">
      <!-- Listing -->
      <div class="fm-listing" :class="{ 'has-preview': selectedFile }">
        <div class="fm-header-row">
          <span class="fm-h-name">Name</span>
          <span class="fm-h-size">Size</span>
          <span class="fm-h-modified">Modified</span>
          <span class="fm-h-actions" />
        </div>
        <div
          v-for="entry in filteredEntries"
          :key="entry.path"
          class="fm-row"
          :class="{ selected: selectedFile?.path === entry.path, 'is-dir': entry.type === 'dir' }"
          @click="navigateTo(entry)"
        >
          <span class="fm-cell-name">
            <span class="fm-icon">{{ entryIcon(entry) }}</span>
            <span class="fm-name-text">{{ entry.name }}</span>
          </span>
          <span class="fm-cell-size">{{ entry.size_formatted }}</span>
          <span class="fm-cell-modified">{{ entry.modified_at?.split(' ')[0] || '' }}</span>
          <span class="fm-cell-actions" @click.stop>
            <button
              v-if="entry.type === 'file'"
              class="fm-action-btn"
              title="Download"
              @click="downloadFile(entry)"
            >⬇</button>
            <button
              class="fm-action-btn danger"
              title="Delete"
              @click="confirmDelete(entry)"
            >🗑</button>
          </span>
        </div>
      </div>

      <!-- Preview -->
      <div v-if="selectedFile" class="fm-preview-panel">
        <div class="fm-preview-header">
          <span class="fm-preview-name">{{ selectedFile.name }}</span>
          <button class="fm-action-btn" @click="selectedFile = null; previewContent = ''">✕</button>
        </div>
        <div v-if="previewLoading" class="fm-loading">Loading preview...</div>
        <FilePreview
          v-else
          :content="previewContent"
          :filename="selectedFile.name"
          :truncated-lines="previewTruncatedLines"
          :truncated-bytes="previewTruncatedBytes"
          :base64-content="previewBase64"
          :mime="previewMime"
          :preview-type="previewType"
        />
      </div>
    </div>

    <!-- Confirm dialog -->
    <Teleport to="body">
      <div v-if="confirmAction" class="confirm-overlay" @click="cancelConfirm">
        <div class="confirm-dialog" @click.stop>
          <div class="confirm-message">{{ confirmAction.message }}</div>
          <div class="confirm-actions">
            <button class="fm-btn" @click="cancelConfirm">Cancel</button>
            <button class="fm-btn danger-btn" @click="confirmAction.onConfirm">Delete</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.file-manager {
  display: flex;
  flex-direction: column;
  height: 100%;
  font-size: 12px;
}

.fm-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 14px;
  border-bottom: 1px solid rgba(255,255,255,0.04);
  flex-wrap: wrap;
}

.fm-breadcrumbs {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-wrap: wrap;
}

.crumb {
  background: none;
  border: none;
  color: rgba(255,255,255,0.4);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
  transition: all 0.2s;
}
.crumb:hover { color: rgba(255,255,255,0.7); }
.crumb.active { color: #9DD522; }
.crumb-sep { color: rgba(255,255,255,0.15); margin-left: 2px; }

.fm-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.fm-search {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 6px;
  padding: 4px 8px;
  font-size: 11px;
  color: rgba(255,255,255,0.7);
  font-family: inherit;
  outline: none;
  width: 120px;
}
.fm-search:focus { border-color: rgba(157,213,34,0.4); }

.fm-file-input {
  position: absolute;
  opacity: 0;
  inset: 0;
  cursor: pointer;
  width: 100%;
}
.fm-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 6px;
  border: 1px solid rgba(233,236,224,0.06);
  background: rgba(233,236,224,0.03);
  color: rgba(233,236,224,0.5);
  font-size: 10.5px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}
.fm-btn:hover { background: rgba(233,236,224,0.07); color: rgba(233,236,224,0.7); }
.danger-btn { border-color: rgba(239,68,68,0.3); color: #EF4444; }
.danger-btn:hover { background: rgba(239,68,68,0.1); }

.fm-error {
  padding: 8px 14px;
  font-size: 11px;
  color: #EF4444;
  background: rgba(239,68,68,0.06);
  border-bottom: 1px solid rgba(239,68,68,0.1);
}

.fm-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px;
  color: rgba(255,255,255,0.3);
  font-size: 12px;
}
.fm-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.06);
  border-top-color: #9DD522;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.fm-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: rgba(255,255,255,0.3);
  text-align: center;
  gap: 6px;
}
.empty-icon { font-size: 32px; opacity: 0.5; }
.empty-hint { font-size: 11px; color: rgba(255,255,255,0.2); }

.fm-body {
  display: flex;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.fm-listing {
  flex: 1;
  overflow-y: auto;
  min-width: 0;
}

.fm-listing.has-preview {
  flex: 0 0 50%;
  max-width: 50%;
  border-right: 1px solid rgba(255,255,255,0.04);
}

.fm-header-row {
  display: flex;
  padding: 6px 14px;
  font-size: 10px;
  font-weight: 600;
  color: rgba(255,255,255,0.25);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  border-bottom: 1px solid rgba(255,255,255,0.03);
  position: sticky;
  top: 0;
  background: #0C0C10;
  z-index: 1;
}

.fm-row {
  display: flex;
  align-items: center;
  padding: 6px 14px;
  cursor: pointer;
  transition: background 0.15s;
  border-bottom: 1px solid rgba(255,255,255,0.02);
}
.fm-row:hover { background: rgba(255,255,255,0.03); }
.fm-row.selected { background: rgba(157,213,34,0.06); }
.fm-row.is-dir { font-weight: 500; }

.fm-h-name, .fm-cell-name { flex: 1; min-width: 0; display: flex; align-items: center; gap: 6px; }
.fm-h-size, .fm-cell-size { width: 60px; flex-shrink: 0; text-align: right; }
.fm-h-modified, .fm-cell-modified { width: 80px; flex-shrink: 0; padding-left: 12px; }
.fm-h-actions, .fm-cell-actions { width: 60px; flex-shrink: 0; display: flex; justify-content: flex-end; gap: 2px; }

.fm-cell-name { overflow: hidden; }
.fm-icon { flex-shrink: 0; font-size: 14px; }
.fm-name-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fm-cell-size, .fm-cell-modified {
  font-size: 11px;
  color: rgba(255,255,255,0.35);
  font-family: 'JetBrains Mono', Menlo, monospace;
}
.fm-cell-size { font-size: 10px; }

.fm-action-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 12px;
  padding: 2px 4px;
  border-radius: 4px;
  color: rgba(255,255,255,0.3);
  transition: all 0.15s;
}
.fm-action-btn:hover { background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.6); }
.fm-action-btn.danger:hover { background: rgba(239,68,68,0.1); color: #EF4444; }

.fm-preview-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.fm-preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  border-bottom: 1px solid rgba(255,255,255,0.04);
}
.fm-preview-name {
  font-family: 'JetBrains Mono', Menlo, monospace;
  font-size: 11px;
  color: rgba(255,255,255,0.5);
}

.confirm-overlay {
  position: fixed;
  inset: 0;
  z-index: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0,0,0,0.5);
}
.confirm-dialog {
  background: #0C0C10;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  padding: 24px;
  min-width: 280px;
  box-shadow: 0 16px 48px rgba(0,0,0,0.6);
}
.confirm-message {
  font-size: 13px;
  color: rgba(255,255,255,0.7);
  margin-bottom: 16px;
  text-align: center;
}
.confirm-actions {
  display: flex;
  justify-content: center;
  gap: 8px;
}

/* Listing scrollbar */
.fm-listing::-webkit-scrollbar { width: 4px; }
.fm-listing::-webkit-scrollbar-track { background: transparent; }
.fm-listing::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.06); border-radius: 2px; }
</style>
