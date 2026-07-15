<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { toastBus } from '@/main'

interface FlixzRun {
  id: string
  agent_id: string | null
  video_path: string
  status: string
  frame_count: number
  duration_seconds: number | null
  resolution: string | null
  transcript_text: string | null
  started_at: string
  completed_at: string | null
}

const config = ref({
  videoPath: '',
  maxFrames: 60,
  fps: 0,
  sceneDetect: true,
  transcript: 'none' as string,
  describe: 'none' as string,
})
const extracting = ref(false)
const runs = ref<FlixzRun[]>([])
const expandedRun = ref<string | null>(null)
const runDetail = ref<any>(null)
const runsLoading = ref(false)

const canExtract = computed(() => config.value.videoPath.trim().length > 0 && !extracting.value)

async function fetchRuns() {
  runsLoading.value = true
  try {
    const res = await fetch('/api/flixz/runs?limit=30')
    if (res.ok) {
      const data = await res.json()
      runs.value = data.runs || []
    }
  } catch { /* ignore */ }
  finally { runsLoading.value = false }
}

async function doExtract() {
  if (!canExtract.value) return
  extracting.value = true
  try {
    const res = await fetch('/api/flixz/extract', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        video_path: config.value.videoPath.trim(),
        max_frames: config.value.maxFrames,
        fps: config.value.fps,
        scene_detect: config.value.sceneDetect,
        transcript: config.value.transcript,
        describe: config.value.describe,
      }),
    })
    const data = await res.json()
    if (data.status === 'completed') {
      runDetail.value = data
      expandedRun.value = data.run_id
      toastBus.success(`Extracted ${data.frame_count} frames`)
      await fetchRuns()
    } else {
      toastBus.error(data.error_message || 'Extraction failed')
    }
  } catch (e: any) {
    toastBus.error(e.message || 'Extraction failed')
  } finally {
    extracting.value = false
  }
}

async function toggleRun(runId: string) {
  if (expandedRun.value === runId) {
    expandedRun.value = null
    runDetail.value = null
    return
  }
  expandedRun.value = runId
  try {
    const res = await fetch(`/api/flixz/runs/${runId}`)
    if (res.ok) runDetail.value = await res.json()
  } catch { runDetail.value = null }
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

function statusColor(status: string): string {
  switch (status) {
    case 'completed': return 'text-success'
    case 'failed': return 'text-danger'
    case 'running': return 'text-warning'
    default: return 'text-text-tertiary'
  }
}

onMounted(fetchRuns)
</script>

<template>
  <div class="sys-flixz">
    <!-- Header -->
    <div class="sys-flixz-header section-bar">
      <div class="sys-flixz-brand">
        <span class="sys-flixz-icon">🎞</span>
        <div>
          <div class="sys-flixz-title">Flixz (general)</div>
          <div class="sys-flixz-sub">Operator tool — system-level extract via /api/flixz (no agent)</div>
        </div>
      </div>
    </div>

    <!-- Config -->
    <div class="sys-flixz-config">
      <div class="sys-flixz-field">
        <label class="sys-flixz-label">Video Path / URL</label>
        <input
          v-model="config.videoPath"
          type="text"
          class="input-base w-full text-xs"
          placeholder="~/.pi/flixz/input/video.mp4 or https://..."
          @keyup.enter="doExtract"
        />
        <p class="sys-flixz-hint">
          Local files must be under ~/.pi/flixz/input (or PI_FLIXZ_ALLOW_ROOTS). HTTP(S) URLs use yt-dlp.
        </p>
      </div>

      <div class="sys-flixz-row">
        <div class="sys-flixz-field flex-1">
          <label class="sys-flixz-label">Max Frames</label>
          <input v-model.number="config.maxFrames" type="number" min="1" max="500" class="input-base w-full text-xs" />
        </div>
        <div class="sys-flixz-field flex-1">
          <label class="sys-flixz-label">FPS (0=auto)</label>
          <input v-model.number="config.fps" type="number" min="0" max="30" class="input-base w-full text-xs" />
        </div>
      </div>

      <div class="sys-flixz-row">
        <div class="sys-flixz-field flex-1">
          <label class="sys-flixz-label">Transcription</label>
          <select v-model="config.transcript" class="input-base w-full text-xs">
            <option value="none">None</option>
            <option value="native">Native (macOS VoiceKit)</option>
          </select>
        </div>
        <div class="sys-flixz-field flex-1">
          <label class="sys-flixz-label">Frame Description</label>
          <select v-model="config.describe" class="input-base w-full text-xs">
            <option value="none">None</option>
            <option value="gemini">Gemini Vision</option>
            <option value="claude">Claude Vision</option>
          </select>
        </div>
      </div>

      <label class="sys-flixz-check">
        <input v-model="config.sceneDetect" type="checkbox" class="accent-lime" />
        Scene Detection
      </label>

      <button
        class="sys-flixz-btn"
        :disabled="!canExtract"
        @click="doExtract"
      >
        <span v-if="extracting" class="sys-flixz-spinner" />
        {{ extracting ? 'Extracting...' : 'Extract Frames' }}
      </button>
    </div>

    <!-- Recent runs -->
    <div class="sys-flixz-runs">
      <div class="sys-flixz-runs-header">
        <span class="text-[10px] font-semibold text-text-muted uppercase tracking-wider">Recent Runs</span>
        <button class="text-[9px] text-text-muted hover:text-text-secondary transition-colors" @click="fetchRuns">Refresh</button>
      </div>

      <div v-if="runsLoading" class="text-xs text-text-tertiary text-center py-8">Loading...</div>

      <div v-else-if="runs.length === 0" class="text-xs text-text-tertiary text-center py-8">
        No extractions yet. Paste a video path above to get started.
      </div>

      <template v-else>
        <button
          v-for="run in runs"
          :key="run.id"
          class="sys-flixz-run-row"
          @click="toggleRun(run.id)"
        >
          <div class="flex items-center gap-2 flex-1 min-w-0">
            <span class="w-2 h-2 rounded-full shrink-0" :class="run.status === 'completed' ? 'bg-success' : run.status === 'failed' ? 'bg-danger' : 'bg-warning'" />
            <span class="text-xs text-text-secondary truncate">{{ run.video_path.split('/').pop() || run.video_path }}</span>
          </div>
          <div class="flex items-center gap-3 shrink-0">
            <span v-if="run.frame_count" class="text-[10px] text-text-muted">{{ run.frame_count }} frames</span>
            <span class="text-[10px]" :class="statusColor(run.status)">{{ run.status }}</span>
            <span class="text-[9px] text-text-muted">{{ timeAgo(run.started_at) }}</span>
          </div>
        </button>
      </template>

      <!-- Expanded detail -->
      <div v-if="expandedRun && runDetail" class="sys-flixz-detail">
        <div class="sys-flixz-detail-grid">
          <div class="sys-flixz-stat">
            <span class="sys-flixz-stat-val">{{ runDetail.duration_seconds?.toFixed(1) || '?' }}s</span>
            <span class="sys-flixz-stat-label">Duration</span>
          </div>
          <div class="sys-flixz-stat">
            <span class="sys-flixz-stat-val">{{ runDetail.frame_count || 0 }}</span>
            <span class="sys-flixz-stat-label">Frames</span>
          </div>
          <div class="sys-flixz-stat">
            <span class="sys-flixz-stat-val">{{ runDetail.resolution || '?' }}</span>
            <span class="sys-flixz-stat-label">Resolution</span>
          </div>
          <div class="sys-flixz-stat">
            <span class="sys-flixz-stat-val">{{ runDetail.output_dir?.split('/').pop() || runDetail.run_id?.slice(0, 8) }}</span>
            <span class="sys-flixz-stat-label">Output Dir</span>
          </div>
        </div>
        <div v-if="runDetail.transcript" class="sys-flixz-transcript">
          <div class="text-[10px] font-semibold text-text-muted mb-1">Transcript</div>
          <div class="text-[10px] text-text-tertiary font-mono whitespace-pre-wrap max-h-24 overflow-y-auto">{{ runDetail.transcript.slice(0, 500) }}</div>
        </div>
        <div v-if="runDetail.error_message" class="sys-flixz-error">{{ runDetail.error_message }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sys-flixz {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
}

.sys-flixz-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sys-flixz-brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.sys-flixz-icon {
  font-size: 24px;
}

.sys-flixz-title {
  font-size: 13px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.75);
}

.sys-flixz-sub {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.25);
}

.sys-flixz-config {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(255, 255, 255, 0.02);
}

.sys-flixz-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sys-flixz-hint {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.28);
  line-height: 1.35;
  margin-top: 4px;
}
.sys-flixz-label {
  font-size: 10px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.3);
}

.sys-flixz-label::after { content: none; }

.sys-flixz-row {
  display: flex;
  gap: 10px;
}

.sys-flixz-check {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
  cursor: pointer;
}

.sys-flixz-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 8px 0;
  border-radius: 10px;
  border: none;
  background: rgba(157, 213, 34, 0.12);
  color: #9DD522;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}

.sys-flixz-btn:hover:not(:disabled) {
  background: rgba(157, 213, 34, 0.2);
}

.sys-flixz-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.sys-flixz-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(157, 213, 34, 0.2);
  border-top-color: #9DD522;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.sys-flixz-runs-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.sys-flixz-run-row {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 10px;
  text-align: left;
  border: none;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  background: transparent;
  cursor: pointer;
  transition: background 0.15s;
  font-family: inherit;
}

.sys-flixz-run-row:hover {
  background: rgba(255, 255, 255, 0.02);
}

.sys-flixz-detail {
  margin-top: 10px;
  padding: 12px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(255, 255, 255, 0.02);
}

.sys-flixz-detail-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-bottom: 8px;
}

.sys-flixz-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.sys-flixz-stat-val {
  font-size: 12px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.7);
}

.sys-flixz-stat-label {
  font-size: 9px;
  color: rgba(255, 255, 255, 0.25);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.sys-flixz-transcript {
  padding: 8px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.02);
}

.sys-flixz-error {
  font-size: 11px;
  color: #EF4444;
  padding: 6px 8px;
  border-radius: 6px;
  background: rgba(239, 68, 68, 0.06);
}
</style>
