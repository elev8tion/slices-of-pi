<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { toastBus } from '@/main'
import { useAppStore } from '@/stores/app'

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
  output_dir?: string
  error_message?: string | null
}

const store = useAppStore()

const config = ref({
  videoPath: '',
  maxFrames: 60,
  fps: 0,
  sceneDetect: true,
  /** none | auto | mlx | captions | native */
  transcript: 'auto' as string,
  describe: 'none' as string,
  describeModel: '' as string,
  /** full | frames_only | transcript_only */
  mode: 'full' as string,
  trashSourceVideo: true,
})
const extracting = ref(false)
const runs = ref<FlixzRun[]>([])
const expandedRun = ref<string | null>(null)
const runDetail = ref<any>(null)
const runsLoading = ref(false)
const visionModels = ref<{ id: string; label: string; provider: string; providerLabel: string }[]>([])
const sttStatus = ref<any>(null)

// Discuss-with-agent
const discussAgentId = ref('')
const discussMessage = ref('')
const discussStreaming = ref(false)
const discussReply = ref('')
const trashing = ref(false)

const canExtract = computed(() => config.value.videoPath.trim().length > 0 && !extracting.value)

const describeModelOptions = computed(() => {
  const d = config.value.describe
  if (d === 'claude') {
    return visionModels.value.filter(m =>
      m.provider.includes('anthropic') || m.id.toLowerCase().includes('claude'),
    )
  }
  if (d === 'openai' || d === 'openai-codex') {
    return visionModels.value.filter(m =>
      m.provider === 'openai-codex'
      || m.provider.includes('openai')
      || m.id.toLowerCase().includes('gpt'),
    )
  }
  if (d === 'grok' || d === 'xai' || d === 'xai-auth') {
    return visionModels.value.filter(m =>
      m.provider.includes('xai') || m.id.toLowerCase().includes('grok'),
    )
  }
  return []
})

const agentOptions = computed(() => store.agents.filter(a => a.name))

const transcriptPreview = computed(() => {
  const t = runDetail.value?.transcript || runDetail.value?.transcript_text || ''
  return typeof t === 'string' ? t : ''
})

async function loadVisionModels() {
  try {
    const res = await fetch('/api/system/models?images_only=true')
    if (!res.ok) return
    const data = await res.json()
    visionModels.value = data.flat || []
  } catch { /* optional */ }
}

async function loadSttStatus() {
  try {
    const res = await fetch('/api/flixz/stt-status')
    if (res.ok) sttStatus.value = await res.json()
  } catch { /* optional */ }
}

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
  discussReply.value = ''
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
        describe_model: config.value.describeModel || undefined,
        mode: config.value.mode,
        trash_source_video: config.value.trashSourceVideo,
      }),
    })
    const data = await res.json()
    if (data.status === 'completed') {
      runDetail.value = data
      expandedRun.value = data.run_id
      const bits: string[] = []
      if (data.frame_count) bits.push(`${data.frame_count} frames`)
      if (data.transcript) bits.push(`transcript ${data.transcript.length} chars via ${data.transcript_provider || '?'}`)
      if (data.trashed_videos?.length) bits.push('source video → Trash')
      toastBus.success(bits.join(' · ') || 'Flixz complete')
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
  discussReply.value = ''
  try {
    const res = await fetch(`/api/flixz/runs/${runId}`)
    if (res.ok) runDetail.value = await res.json()
  } catch { runDetail.value = null }
}

async function trashArtifacts(what: 'video' | 'frames' | 'all') {
  const id = expandedRun.value || runDetail.value?.run_id || runDetail.value?.id
  if (!id) return
  if (what === 'all' && !confirm('Trash this entire Flixz run (frames, audio, brief) and remove the DB record?')) return
  trashing.value = true
  try {
    const res = await fetch(`/api/flixz/runs/${id}/trash`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ what }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || 'Trash failed')
    toastBus.success(what === 'all' ? 'Run moved to Trash' : `Trashed ${what}`)
    if (what === 'all') {
      expandedRun.value = null
      runDetail.value = null
    }
    await fetchRuns()
  } catch (e: any) {
    toastBus.error(e.message || 'Trash failed')
  } finally {
    trashing.value = false
  }
}

async function discussWithAgent() {
  const id = expandedRun.value || runDetail.value?.run_id || runDetail.value?.id
  if (!id) return
  if (!discussAgentId.value) {
    toastBus.error('Pick a local agent to discuss with')
    return
  }
  discussStreaming.value = true
  discussReply.value = ''
  try {
    const res = await fetch(`/api/flixz/runs/${id}/discuss`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        agent_id: discussAgentId.value,
        message: discussMessage.value || '',
        stream: true,
      }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || `HTTP ${res.status}`)
    }
    const reader = res.body?.getReader()
    if (!reader) throw new Error('No stream')
    const dec = new TextDecoder()
    let buf = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += dec.decode(value, { stream: true })
      const parts = buf.split('\n\n')
      buf = parts.pop() || ''
      for (const part of parts) {
        const line = part.split('\n').find(l => l.startsWith('data: '))
        if (!line) continue
        try {
          const ev = JSON.parse(line.slice(6))
          if (ev.type === 'text_delta' && ev.content) discussReply.value += ev.content
          if (ev.type === 'error') toastBus.error(ev.content || 'Agent error')
        } catch { /* skip */ }
      }
    }
    toastBus.success('Agent finished — continue in Agents → Chat if you want a longer session')
    // Open agent workspace for follow-up
    store.openAgentFromCommand(discussAgentId.value, 'chat')
  } catch (e: any) {
    toastBus.error(e.message || 'Discuss failed')
  } finally {
    discussStreaming.value = false
  }
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

function setTranscriptOnly() {
  config.value.mode = 'transcript_only'
  if (config.value.transcript === 'none') config.value.transcript = 'auto'
  config.value.describe = 'none'
}

onMounted(() => {
  fetchRuns()
  loadVisionModels()
  loadSttStatus()
  store.fetchAgents()
})
</script>

<template>
  <div class="sys-flixz">
    <div class="sys-flixz-header section-bar">
      <div class="sys-flixz-brand">
        <span class="sys-flixz-icon">🎞</span>
        <div>
          <div class="sys-flixz-title">Flixz (general)</div>
          <div class="sys-flixz-sub">
            Frames · transcript · discuss with a local pi agent · trash when done
          </div>
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
          placeholder="~/.pi/flixz/input/video.mp4 or https://youtube.com/..."
          @keyup.enter="doExtract"
        />
        <p class="sys-flixz-hint">
          Local: under ~/.pi/flixz/input (or PI_FLIXZ_ALLOW_ROOTS). URLs use yt-dlp.
        </p>
      </div>

      <!-- Mode pills -->
      <div class="sys-flixz-field">
        <label class="sys-flixz-label">Mode</label>
        <div class="mode-pills">
          <button type="button" class="mode-pill" :class="{ active: config.mode === 'full' }" @click="config.mode = 'full'">
            Full (frames + STT)
          </button>
          <button type="button" class="mode-pill" :class="{ active: config.mode === 'transcript_only' }" @click="setTranscriptOnly">
            Transcript only
          </button>
          <button type="button" class="mode-pill" :class="{ active: config.mode === 'frames_only' }" @click="config.mode = 'frames_only'; config.transcript = 'none'">
            Frames only
          </button>
        </div>
      </div>

      <div class="sys-flixz-row" v-if="config.mode !== 'transcript_only'">
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
          <select v-model="config.transcript" class="input-base w-full text-xs" :disabled="config.mode === 'frames_only'">
            <option value="none">None</option>
            <option value="auto">Auto (captions → MLX → VoiceKit) — never Parakeet</option>
            <option value="mlx">MLX Whisper (primary local STT)</option>
            <option value="parakeet">Parakeet ONNX / Handy (secondary — verify vs MLX)</option>
            <option value="compare">Compare MLX + Parakeet (side-by-side)</option>
            <option value="captions">YouTube captions only (fast)</option>
            <option value="native">VoiceKit (short clips only)</option>
          </select>
          <p class="sys-flixz-hint">
            <strong>Parakeet</strong> uses Handy’s local ONNX models
            (<code>~/Library/Application Support/com.pais.handy/models/…</code>).
            It is a <em>secondary</em> option only — not used by Auto. Use <strong>Compare</strong>
            to run both MLX and Parakeet and verify them against each other.
            <span v-if="sttStatus?.parakeet"> · Parakeet: {{ sttStatus.parakeet.available ? 'ready' : sttStatus.parakeet.detail }}</span>
          </p>
        </div>
        <div class="sys-flixz-field flex-1" v-if="config.mode !== 'transcript_only'">
          <label class="sys-flixz-label">Frame Description</label>
          <select v-model="config.describe" class="input-base w-full text-xs" @change="config.describeModel = ''">
            <option value="none">None (frames only)</option>
            <option value="openai">OpenAI Codex (OAuth)</option>
            <option value="grok">Grok / xAI (OAuth)</option>
            <option value="claude">Claude Vision (OAuth)</option>
          </select>
        </div>
      </div>

      <div v-if="config.describe !== 'none' && describeModelOptions.length && config.mode !== 'transcript_only'" class="sys-flixz-field">
        <label class="sys-flixz-label">Vision model</label>
        <select v-model="config.describeModel" class="input-base w-full text-xs">
          <option value="">Default for backend</option>
          <option v-for="m in describeModelOptions" :key="m.id" :value="m.id">
            {{ m.providerLabel }} / {{ m.label }}
          </option>
        </select>
      </div>

      <label v-if="config.mode !== 'transcript_only'" class="sys-flixz-check">
        <input v-model="config.sceneDetect" type="checkbox" class="accent-lime" />
        Scene Detection
      </label>

      <label v-if="config.mode !== 'transcript_only'" class="sys-flixz-check">
        <input v-model="config.trashSourceVideo" type="checkbox" class="accent-lime" />
        Move source MP4 to Trash after frames extract
      </label>

      <button class="sys-flixz-btn" :disabled="!canExtract" @click="doExtract">
        <span v-if="extracting" class="sys-flixz-spinner" />
        {{ extracting
          ? (config.mode === 'transcript_only' ? 'Transcribing…' : 'Extracting…')
          : (config.mode === 'transcript_only' ? 'Get transcript' : 'Extract Frames') }}
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
        No extractions yet. Paste a path or YouTube URL above.
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
            <span v-if="run.transcript_text" class="text-[10px] text-accent/70">txt</span>
            <span class="text-[10px]" :class="statusColor(run.status)">{{ run.status }}</span>
            <span class="text-[9px] text-text-muted">{{ timeAgo(run.started_at) }}</span>
          </div>
        </button>
      </template>

      <!-- Expanded detail -->
      <div v-if="expandedRun && runDetail" class="sys-flixz-detail">
        <div class="sys-flixz-detail-grid">
          <div class="sys-flixz-stat">
            <span class="sys-flixz-stat-val">{{ runDetail.duration_seconds?.toFixed?.(1) ?? runDetail.duration_seconds ?? '?' }}s</span>
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
            <span class="sys-flixz-stat-val">{{ (runDetail.output_dir || '').split('/').pop() || (runDetail.run_id || runDetail.id || '').slice(0, 8) }}</span>
            <span class="sys-flixz-stat-label">Output</span>
          </div>
        </div>

        <div v-if="transcriptPreview" class="sys-flixz-transcript">
          <div class="text-[10px] font-semibold text-text-muted mb-1">
            Transcript
            <span v-if="runDetail.transcript_provider" class="text-text-tertiary font-normal">
              ({{ runDetail.transcript_provider }})
            </span>
            · {{ transcriptPreview.length }} chars
          </div>
          <div class="text-[11px] text-text-secondary font-mono whitespace-pre-wrap max-h-48 overflow-y-auto">{{ transcriptPreview }}</div>
        </div>
        <div v-else class="sys-flixz-transcript">
          <div class="text-[10px] text-text-tertiary">No transcript stored. Re-run with Auto / MLX / Parakeet / Compare.</div>
        </div>

        <!-- Side-by-side compare results -->
        <div v-if="runDetail.transcript_compare" class="compare-box">
          <div class="text-[10px] font-semibold text-accent uppercase tracking-wider mb-2">
            STT compare (verify against each other)
          </div>
          <div class="compare-grid">
            <div v-for="(data, name) in runDetail.transcript_compare" :key="name" class="compare-col">
              <div class="compare-head">
                {{ name }}
                <span class="compare-meta">
                  {{ data.ok ? `${data.chars} chars · ${data.segment_count} segs` : 'failed' }}
                </span>
              </div>
              <div v-if="data.error" class="text-[10px] text-danger">{{ data.error }}</div>
              <div v-else class="text-[10px] text-text-secondary font-mono whitespace-pre-wrap max-h-40 overflow-y-auto">
                {{ data.text || '_(empty)_' }}
              </div>
            </div>
          </div>
          <p class="sys-flixz-hint mt-2">
            Full files: <code>transcript_mlx.txt</code>, <code>transcript_parakeet.txt</code>,
            <code>transcript_compare.md</code> in the run output dir.
          </p>
        </div>

        <div v-if="runDetail.error_message" class="sys-flixz-error">{{ runDetail.error_message }}</div>

        <!-- Trash actions -->
        <div class="action-row">
          <button type="button" class="action-btn" :disabled="trashing" @click="trashArtifacts('video')">
            Trash source video
          </button>
          <button type="button" class="action-btn" :disabled="trashing" @click="trashArtifacts('frames')">
            Trash frames
          </button>
          <button type="button" class="action-btn action-btn-danger" :disabled="trashing" @click="trashArtifacts('all')">
            Trash entire run
          </button>
        </div>

        <!-- Discuss with agent -->
        <div class="discuss-box">
          <div class="text-[10px] font-semibold text-text-muted uppercase tracking-wider mb-2">
            Discuss with agent
          </div>
          <p class="sys-flixz-hint mb-2">
            Sends transcript + frame descriptions + paths to a local pi agent so you can plan what to do with the material.
          </p>
          <div class="sys-flixz-row mb-2">
            <div class="sys-flixz-field flex-1">
              <label class="sys-flixz-label">Agent</label>
              <select v-model="discussAgentId" class="input-base w-full text-xs">
                <option value="">Select agent…</option>
                <option v-for="a in agentOptions" :key="a.id" :value="a.id">
                  {{ a.name }} ({{ a.status }})
                </option>
              </select>
            </div>
          </div>
          <div class="sys-flixz-field mb-2">
            <label class="sys-flixz-label">What do you want to do? (optional)</label>
            <textarea
              v-model="discussMessage"
              class="input-base w-full text-xs"
              rows="2"
              placeholder="e.g. Summarize the video and draft a short script from the transcript…"
            />
          </div>
          <button
            type="button"
            class="sys-flixz-btn"
            :disabled="discussStreaming || !discussAgentId"
            @click="discussWithAgent"
          >
            <span v-if="discussStreaming" class="sys-flixz-spinner" />
            {{ discussStreaming ? 'Agent thinking…' : 'Discuss with agent' }}
          </button>
          <div v-if="discussReply" class="discuss-reply">
            <div class="text-[10px] font-semibold text-accent mb-1">Agent reply</div>
            <div class="text-[11px] text-text-secondary whitespace-pre-wrap max-h-64 overflow-y-auto">{{ discussReply }}</div>
          </div>
        </div>
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
.sys-flixz-icon { font-size: 24px; }
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
.sys-flixz-row {
  display: flex;
  gap: 10px;
}
.mode-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.mode-pill {
  font-size: 11px;
  font-weight: 500;
  font-family: inherit;
  padding: 6px 12px;
  border-radius: 9999px;
  border: 1px solid rgba(255,255,255,0.08);
  background: rgba(255,255,255,0.03);
  color: rgba(255,255,255,0.45);
  cursor: pointer;
  transition: all 0.2s;
}
.mode-pill.active {
  background: rgba(157, 213, 34, 0.12);
  border-color: rgba(157, 213, 34, 0.35);
  color: #9DD522;
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
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.sys-flixz-detail-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
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
.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.action-btn {
  font-size: 11px;
  font-weight: 500;
  font-family: inherit;
  padding: 6px 12px;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.1);
  background: rgba(255,255,255,0.03);
  color: rgba(255,255,255,0.55);
  cursor: pointer;
}
.action-btn:hover:not(:disabled) {
  border-color: rgba(157,213,34,0.3);
  color: #9DD522;
}
.action-btn-danger:hover:not(:disabled) {
  border-color: rgba(239,68,68,0.4);
  color: #EF4444;
}
.action-btn:disabled { opacity: 0.4; }
.discuss-box {
  padding: 12px;
  border-radius: 10px;
  border: 1px solid rgba(157, 213, 34, 0.15);
  background: rgba(157, 213, 34, 0.04);
}
.discuss-reply {
  margin-top: 10px;
  padding: 10px;
  border-radius: 8px;
  background: rgba(0,0,0,0.25);
  border: 1px solid rgba(255,255,255,0.06);
}
.mb-2 { margin-bottom: 8px; }
.mt-2 { margin-top: 8px; }
.flex-1 { flex: 1; min-width: 0; }
.compare-box {
  padding: 12px;
  border-radius: 10px;
  border: 1px solid rgba(157, 213, 34, 0.2);
  background: rgba(157, 213, 34, 0.05);
}
.compare-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
@media (max-width: 700px) {
  .compare-grid { grid-template-columns: 1fr; }
}
.compare-col {
  padding: 8px;
  border-radius: 8px;
  background: rgba(0,0,0,0.25);
  border: 1px solid rgba(255,255,255,0.06);
  min-width: 0;
}
.compare-head {
  font-size: 11px;
  font-weight: 600;
  color: #9DD522;
  margin-bottom: 6px;
  display: flex;
  justify-content: space-between;
  gap: 8px;
}
.compare-meta {
  font-weight: 400;
  color: rgba(255,255,255,0.35);
  font-size: 10px;
}
</style>
