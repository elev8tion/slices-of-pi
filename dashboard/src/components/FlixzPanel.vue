<script setup lang="ts">
import { ref, computed } from 'vue'
import { toastBus } from '@/main'

const props = defineProps<{ agentId: string }>()

// ── State ─────────────────────────────────────────────────────

const videoPath = ref('')
const processing = ref(false)
const activeTab = ref<'config' | 'results'>('config')
const lastResult = ref<any>(null)
const selectedSinks = ref<string[]>([])
const availableSinks = ref<string[]>([])
const sinksLoading = ref(false)
const configExpanded = ref(false)

// Preset config
const config = ref({
  fps: 0,
  sceneDetect: true,
  transcript: 'none' as 'none' | 'native',
  describe: 'none' as 'none' | 'gemini' | 'claude',
  maxFrames: 60,
  sinks: [] as string[],
})

// ── Recent runs ───────────────────────────────────────────────

const recentRuns = ref<Array<{dir: string, name: string, time: string}>>([])

// ── Computed ──────────────────────────────────────────────────

const canProcess = computed(() => videoPath.value.trim().length > 0 && !processing.value)

const frameCount = computed(() => {
  if (!lastResult.value?.frames) return 0
  return lastResult.value.frames.length
})

const transcriptText = computed(() => {
  if (typeof lastResult.value?.transcript === 'string') return lastResult.value.transcript
  return ''
})

const transcriptSegments = computed(() => {
  if (Array.isArray(lastResult.value?.transcript_segments)) return lastResult.value.transcript_segments
  return []
})

// ── Methods ───────────────────────────────────────────────────

async function processVideo() {
  if (!canProcess.value) return
  processing.value = true
  activeTab.value = 'results'

  try {
    // Call the Flixz backend endpoint directly
    const res = await fetch(`/api/agents/${props.agentId}/flixz/extract`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        video_path: videoPath.value.trim(),
        max_frames: config.value.maxFrames,
        fps: config.value.fps,
        scene_detect: config.value.sceneDetect,
        transcript: config.value.transcript,
        describe: config.value.describe,
      }),
    })

    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || data.error_message || `HTTP ${res.status}`)

    if (data.status === 'completed') {
      lastResult.value = data
      recentRuns.value.unshift({
        dir: data.output_dir || `~/flixz/output/${data.run_id}`,
        name: videoPath.value.split('/').pop() || 'video',
        time: new Date().toLocaleString(),
      })
      if (recentRuns.value.length > 20) recentRuns.value = recentRuns.value.slice(0, 20)
      toastBus.success(`Extracted ${data.frame_count} frames`)
    } else {
      throw new Error(data.error_message || 'Extraction failed')
    }
  } catch (e: any) {
    toastBus.error(e.message || 'Failed to process video')
  } finally {
    processing.value = false
  }
}

function loadDemo(name: string) {
  videoPath.value = name
}

function clearResult() {
  lastResult.value = null
  activeTab.value = 'config'
}
</script>

<template>
  <div class="flixz-panel">
    <!-- Header -->
    <div class="flixz-header">
      <div class="flixz-brand">
        <!-- Slice of Pi logo replacement — no flixz branding -->
        <img src="/logo-nav.png" alt="Slice of Pi" class="flixz-logo" />
        <div class="flixz-title-section">
          <span class="flixz-title">Frame Extraction</span>
          <span class="flixz-subtitle">Video → frames → transcript for LLM analysis</span>
        </div>
      </div>
    </div>

    <!-- Config Tab -->
    <div v-if="activeTab === 'config'" class="flixz-config">
      <!-- Video Input -->
      <div class="flixz-section">
        <label class="flixz-label">Video Path / URL</label>
        <div class="flixz-input-row">
          <input
            v-model="videoPath"
            type="text"
            class="input-base flex-1 text-xs"
            placeholder="/path/to/video.mp4 or https://... or drag a file"
            @keyup.enter="processVideo"
          />
        </div>
        <div class="flixz-demos">
          <span class="text-[9px] text-text-muted">Demos:</span>
          <button v-for="d in ['~/demo/sample.mp4', 'https://example.com/video.mp4']" :key="d"
            class="flixz-demo-chip"
            @click="loadDemo(d)"
          >{{ d.split('/').pop() }}</button>
        </div>
      </div>

      <!-- Processing Config (collapsible) -->
      <div class="flixz-section">
        <button class="flixz-collapse-toggle" @click="configExpanded = !configExpanded">
          <svg class="w-3 h-3 transition-transform" :class="{ 'rotate-90': configExpanded }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
          </svg>
          <span class="text-[11px] font-medium text-text-secondary">Processing Options</span>
        </button>

        <div v-if="configExpanded" class="flixz-config-grid">
          <div class="flixz-config-field">
            <label class="text-[10px] text-text-muted">Max Frames</label>
            <input v-model.number="config.maxFrames" type="number" min="1" max="500" class="input-base w-full text-xs" />
          </div>
          <div class="flixz-config-field">
            <label class="text-[10px] text-text-muted">FPS (0 = auto/scene detect)</label>
            <input v-model.number="config.fps" type="number" min="0" max="30" class="input-base w-full text-xs" />
          </div>
          <div class="flixz-config-field">
            <label class="text-[10px] text-text-muted">Scene Detection</label>
            <label class="flex items-center gap-2 text-xs text-text-secondary mt-1">
              <input v-model="config.sceneDetect" type="checkbox" class="accent-lime" />
              {{ config.sceneDetect ? 'Enabled' : 'Disabled' }}
            </label>
          </div>
          <div class="flixz-config-field">
            <label class="text-[10px] text-text-muted">Transcription</label>
            <select v-model="config.transcript" class="flixz-select">
              <option value="none">None</option>
              <option value="native">Apple On-Device (Native)</option>
            </select>
          </div>
          <div class="flixz-config-field">
            <label class="text-[10px] text-text-muted">Frame Description</label>
            <select v-model="config.describe" class="flixz-select">
              <option value="none">None (frames only)</option>
              <option value="openai">OpenAI Codex (OAuth)</option>
              <option value="grok">Grok / xAI</option>
              <option value="claude">Claude Vision</option>
            </select>
            <p class="flixz-hint">
              Same OAuth as pi (openai-codex / xai-auth / anthropic). Create agent still has full chat models.
            </p>
          </div>
        </div>
      </div>

      <!-- Run Button -->
      <div class="flixz-actions">
        <button
          class="flixz-run-btn"
          :class="{ running: processing }"
          :disabled="!canProcess"
          @click="processVideo"
        >
          <svg v-if="processing" class="animate-spin w-3.5 h-3.5" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
          </svg>
          <svg v-else class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          {{ processing ? 'Processing...' : 'Extract Frames' }}
        </button>
      </div>

      <!-- Recent runs -->
      <div v-if="recentRuns.length > 0" class="flixz-section">
        <div class="text-[10px] font-semibold text-text-muted uppercase tracking-wider mb-2">Recent Runs</div>
        <div v-for="run in recentRuns.slice(0, 5)" :key="run.dir" class="flixz-run-row">
          <span class="text-xs text-text-secondary">{{ run.name }}</span>
          <span class="text-[10px] text-text-tertiary">{{ run.time }}</span>
        </div>
      </div>
    </div>

    <!-- Results Tab -->
    <div v-else class="flixz-results">
      <!-- Results toolbar -->
      <div class="flixz-results-toolbar">
        <button class="flixz-back-btn" @click="clearResult">
          <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
          </svg>
          New Extraction
        </button>
        <span class="text-[10px] text-text-muted">
          {{ frameCount }} frames
          <span v-if="transcriptText"> · {{ transcriptText.length > 0 ? 'has transcript' : 'no transcript' }}</span>
        </span>
      </div>

      <!-- No results state -->
      <div v-if="!lastResult" class="flixz-empty">
        <div class="text-2xl mb-2 opacity-30">🎞</div>
        <div class="text-sm text-text-tertiary">Processing video...</div>
      </div>

      <!-- Results display -->
      <div v-else class="flixz-result-body">
        <!-- Summary card -->
        <div class="flixz-summary-card">
          <div class="flixz-summary-grid">
            <div class="flixz-stat">
              <span class="flixz-stat-value">{{ lastResult.duration_seconds?.toFixed(1) || lastResult.video?.durationSeconds?.toFixed(1) || '?' }}s</span>
              <span class="flixz-stat-label">Duration</span>
            </div>
            <div class="flixz-stat">
              <span class="flixz-stat-value">{{ frameCount }}</span>
              <span class="flixz-stat-label">Frames</span>
            </div>
            <div class="flixz-stat">
              <span class="flixz-stat-value">{{ lastResult.resolution || (lastResult.video ? lastResult.video.width + '×' + lastResult.video.height : '?') }}</span>
              <span class="flixz-stat-label">Resolution</span>
            </div>
            <div class="flixz-stat">
              <span class="flixz-stat-value">{{ (lastResult.sinks || []).length || 0 }}</span>
              <span class="flixz-stat-label">Sinks</span>
            </div>
          </div>
        </div>

        <!-- Frame thumbnails -->
        <div v-if="lastResult.frames?.length" class="flixz-section">
          <div class="text-[11px] font-semibold text-text-secondary mb-2">
            Frames ({{ lastResult.frames.length }})
          </div>
          <div class="flixz-frame-grid">
            <div v-for="(frame, i) in lastResult.frames.slice(0, 30)" :key="i" class="flixz-frame-thumb">
              <img
                v-if="typeof frame === 'string' && frame.length > 10"
                :src="'data:image/png;base64,' + frame"
                class="flixz-frame-img"
                :alt="'Frame ' + (i + 1)"
              />
              <div v-else class="flixz-frame-placeholder">
                <span class="text-[9px] text-text-muted">f{{ i + 1 }}</span>
              </div>
            </div>
          </div>
          <div v-if="lastResult.frames.length > 30" class="text-[10px] text-text-muted mt-1">
            + {{ lastResult.frames.length - 30 }} more frames
          </div>
        </div>

        <!-- Transcript -->
        <div v-if="transcriptText" class="flixz-section">
          <div class="text-[11px] font-semibold text-text-secondary mb-1">
            Transcript
            <span v-if="transcriptSegments.length" class="text-[9px] text-text-muted ml-1">
              ({{ transcriptSegments.length }} segments)
            </span>
          </div>
          <div class="flixz-transcript-box">
            <template v-if="transcriptSegments.length">
              <div v-for="seg in transcriptSegments" :key="seg.index" class="flixz-segment-row">
                <span class="flixz-segment-time">{{ seg.start?.toFixed(1) }}s</span>
                <span class="flixz-segment-text">{{ seg.text }}</span>
              </div>
            </template>
            <template v-else>
              {{ transcriptText.slice(0, 500) }}
              <span v-if="transcriptText.length > 500" class="text-lime">...</span>
            </template>
          </div>
        </div>

        <!-- Sinks -->
        <div v-if="lastResult.sinks?.length" class="flixz-section">
          <div class="text-[11px] font-semibold text-text-secondary mb-1">Sinks</div>
          <div v-for="s in lastResult.sinks" :key="s.name" class="flixz-sink-row">
            <span class="text-xs text-text-secondary">{{ s.name }}</span>
            <span class="text-[10px]" :class="s.ok ? 'text-success' : 'text-error'">
              {{ s.ok ? 'OK' : 'Failed' }}
            </span>
            <span v-if="s.durationMs" class="text-[10px] text-text-muted">{{ s.durationMs.toFixed(0) }}ms</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.flixz-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  min-height: 200px;
}

/* Header */
.flixz-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.flixz-brand {
  display: flex;
  align-items: center;
  gap: 10px;
}
.flixz-logo {
  height: 28px;
  width: auto;
}
.flixz-title-section {
  display: flex;
  flex-direction: column;
}
.flixz-title {
  font-family: 'Clash Display', sans-serif;
  font-size: 14px;
  font-weight: 600;
  color: #E9ECE0;
  letter-spacing: -0.02em;
}
.flixz-subtitle {
  font-size: 10px;
  color: rgba(233,236,224,0.3);
  font-weight: 500;
}

/* Sections */
.flixz-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.flixz-label {
  font-size: 10px;
  font-weight: 600;
  color: rgba(233,236,224,0.4);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.flixz-input-row {
  display: flex;
  gap: 6px;
}

/* Demo chips */
.flixz-demos {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
}
.flixz-demo-chip {
  font-size: 9px;
  padding: 2px 8px;
  border-radius: 6px;
  border: 1px solid rgba(255,255,255,0.06);
  background: rgba(255,255,255,0.02);
  color: rgba(157,213,34,0.5);
  cursor: pointer;
  font-family: 'JetBrains Mono', monospace;
  transition: all 0.15s;
}
.flixz-demo-chip:hover {
  background: rgba(157,213,34,0.08);
  border-color: rgba(157,213,34,0.2);
}

/* Collapse toggle */
.flixz-collapse-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px 0;
  color: rgba(233,236,224,0.4);
}
.flixz-collapse-toggle:hover {
  color: rgba(233,236,224,0.6);
}

/* Config grid */
.flixz-config-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  padding: 10px;
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 10px;
}
.flixz-config-field {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.flixz-select {
  background: transparent;
  backdrop-filter: blur(4px);
  border: 1px solid rgba(233,236,224,0.15);
  border-radius: 12px;
  color: rgba(233,236,224,0.6);
  padding: 8px 10px;
  font-size: 11px;
  outline: none;
  font-family: inherit;
}
.flixz-select:focus {
  border-color: #9DD522;
}
.flixz-hint {
  font-size: 10px;
  color: rgba(255,255,255,0.3);
  line-height: 1.35;
  margin-top: 4px;
}

/* Actions */
.flixz-actions {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}
.flixz-run-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 600;
  padding: 8px 20px;
  border-radius: 10px;
  border: none;
  background: rgba(157,213,34,0.12);
  color: #9DD522;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}
.flixz-run-btn:hover:not(:disabled) {
  background: rgba(157,213,34,0.2);
}
.flixz-run-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.flixz-run-btn.running {
  background: rgba(34,197,94,0.12);
  color: #22C55E;
}

/* Recent runs */
.flixz-run-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  border-bottom: 1px solid rgba(255,255,255,0.03);
}

/* Results toolbar */
.flixz-results-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.flixz-back-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  font-weight: 500;
  padding: 4px 10px;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.08);
  background: rgba(255,255,255,0.02);
  color: rgba(233,236,224,0.5);
  cursor: pointer;
  font-family: inherit;
  transition: all 0.15s;
}
.flixz-back-btn:hover {
  background: rgba(255,255,255,0.05);
  color: rgba(233,236,224,0.7);
}

/* Empty state */
.flixz-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 16px;
  text-align: center;
}

/* Summary card */
.flixz-summary-card {
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 12px;
  padding: 14px;
}
.flixz-summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}
.flixz-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
.flixz-stat-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  font-weight: 600;
  color: #9DD522;
}
.flixz-stat-label {
  font-size: 9px;
  color: rgba(233,236,224,0.3);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Frame grid */
.flixz-frame-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
  gap: 6px;
}
.flixz-frame-thumb {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.flixz-frame-placeholder {
  width: 100%;
  aspect-ratio: 16 / 9;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.flixz-frame-img {
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  border-radius: 6px;
  border: 1px solid rgba(255,255,255,0.06);
}

/* Transcript */
.flixz-transcript-box {
  font-size: 11px;
  line-height: 1.5;
  color: rgba(233,236,224,0.5);
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 10px;
  padding: 12px;
  max-height: 200px;
  overflow-y: auto;
  white-space: pre-wrap;
}
.flixz-segment-row {
  display: flex;
  gap: 8px;
  padding: 2px 0;
  align-items: flex-start;
}
.flixz-segment-row + .flixz-segment-row {
  border-top: 1px solid rgba(255,255,255,0.02);
  padding-top: 6px;
  margin-top: 2px;
}
.flixz-segment-time {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #9DD522;
  min-width: 42px;
  flex-shrink: 0;
}
.flixz-segment-text {
  font-size: 11px;
  color: rgba(233,236,224,0.55);
  line-height: 1.5;
}

/* Sink row */
.flixz-sink-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 0;
  border-bottom: 1px solid rgba(255,255,255,0.03);
}

/* Result body scroll */
.flixz-result-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
  max-height: 400px;
  overflow-y: auto;
}
.flixz-result-body::-webkit-scrollbar { width: 4px; }
.flixz-result-body::-webkit-scrollbar-track { background: transparent; }
.flixz-result-body::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.06); border-radius: 2px; }
</style>
