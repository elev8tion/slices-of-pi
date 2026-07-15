<script setup lang="ts">
import { ref, onMounted } from 'vue'
import StatusIndicator from './StatusIndicator.vue'

const props = defineProps<{ agentId: string }>()

const agent = ref<any>(null)
const loading = ref(true)
const error = ref(false)

// Profile data (reactive, no DOM manipulation)
const profileStaticCount = ref<number | string>('—')
const profileDynamicCount = ref<number | string>('—')
const profilePreview = ref('Loading profile...')

async function loadAgent() {
  loading.value = true
  error.value = false
  try {
    const res = await fetch(`/api/agents/${props.agentId}`)
    if (!res.ok) throw new Error('Not found')
    agent.value = await res.json()
  } catch {
    error.value = true
    agent.value = null
  } finally {
    loading.value = false
  }
}

async function loadProfile() {
  try {
    const res = await fetch(`/api/agents/${props.agentId}/profile`)
    if (!res.ok) return
    const data = await res.json()
    profileStaticCount.value = data.static_count ?? 0
    profileDynamicCount.value = data.dynamic_count ?? 0
    if (data.preview) {
      profilePreview.value = data.preview
    } else {
      profilePreview.value = 'No profile data yet. Start a session to build memory.'
    }
  } catch {
    profilePreview.value = 'Failed to load profile.'
  }
}

onMounted(() => {
  loadAgent()
  loadProfile()
})
</script>

<template>
  <div class="info-panel p-6 space-y-5">

    <!-- Loading skeleton -->
    <div v-if="loading" class="space-y-4">
      <div v-for="i in 4" :key="i" class="skeleton-card">
        <div class="skeleton-line w-20 h-3 mb-3" />
        <div class="skeleton-line w-full h-4 mb-2" />
        <div class="skeleton-line w-3/4 h-4" />
      </div>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="text-center py-8">
      <div class="text-2xl mb-2 opacity-30">⚠</div>
      <div class="text-sm text-text-tertiary mb-3">Failed to load agent info</div>
      <button class="btn-retry" @click="loadAgent">Retry</button>
    </div>

    <!-- Info content -->
    <template v-else-if="agent">

      <!-- Overview -->
      <section>
        <div class="section-label">Overview</div>
        <div class="info-grid">
          <div class="info-field">
            <span class="info-key">Name</span>
            <span class="info-val">{{ agent.name }}</span>
          </div>
          <div class="info-field">
            <span class="info-key">Status</span>
            <span class="info-val flex items-center gap-1.5">
              <StatusIndicator :status="agent.status" size="sm" />
              {{ agent.status }}
            </span>
          </div>
          <div class="info-field">
            <span class="info-key">Model</span>
            <span class="info-val font-mono text-[12px]">{{ agent.model || 'default' }}</span>
          </div>
          <div class="info-field">
            <span class="info-key">Created</span>
            <span class="info-val">{{ new Date(agent.created_at).toLocaleDateString() }}</span>
          </div>
          <div class="info-field" v-if="agent.last_active">
            <span class="info-key">Last Active</span>
            <span class="info-val">{{ new Date(agent.last_active).toLocaleDateString() }}</span>
          </div>
          <div class="info-field">
            <span class="info-key">Agent ID</span>
            <span class="info-val font-mono text-[10px] opacity-60">{{ agent.id }}</span>
          </div>
        </div>
      </section>

      <!-- Capabilities -->
      <section>
        <div class="section-label">Capabilities</div>
        <div class="space-y-3">
          <div>
            <div class="info-key mb-1.5">Tools</div>
            <div v-if="(agent.tools || []).length === 0" class="text-xs text-text-tertiary">None configured</div>
            <div v-else class="chip-row">
              <span v-for="t in (agent.tools || [])" :key="t" class="chip chip-tool">{{ t }}</span>
            </div>
          </div>
          <div>
            <div class="info-key mb-1.5">Skills</div>
            <div v-if="(agent.skills || []).length === 0" class="text-xs text-text-tertiary">No skills loaded</div>
            <div v-else class="chip-row">
              <span v-for="s in (agent.skills || [])" :key="s" class="chip chip-skill">{{ s }}</span>
            </div>
          </div>
          <div>
            <div class="info-key mb-1.5">Extensions</div>
            <div v-if="(agent.extensions || []).length === 0" class="text-xs text-text-tertiary">No extensions</div>
            <div v-else class="chip-row">
              <span v-for="e in (agent.extensions || [])" :key="e" class="chip chip-ext">{{ e }}</span>
            </div>
          </div>
        </div>
      </section>

      <!-- Runtime -->
      <section>
        <div class="section-label">Runtime</div>
        <div class="info-grid">
          <div class="info-field">
            <span class="info-key">Context Window</span>
            <span class="info-val">{{ (agent.context_window || 40000).toLocaleString() }} tokens</span>
          </div>
          <div class="info-field">
            <span class="info-key">Auto Compact</span>
            <span class="info-val" :class="agent.auto_compact ? 'text-success' : 'text-text-tertiary'">{{ agent.auto_compact ? 'Enabled' : 'Disabled' }}</span>
          </div>
          <div class="info-field" v-if="agent.persona">
            <span class="info-key">Persona</span>
            <span class="info-val">{{ agent.persona }}</span>
          </div>
          <div class="info-field" v-if="agent.system_prompt">
            <span class="info-key">System Prompt</span>
            <span class="info-val text-[11px] font-mono opacity-70 max-h-16 overflow-y-auto">{{ agent.system_prompt }}</span>
          </div>
        </div>
      </section>

      <!-- Usage -->
      <section>
        <div class="section-label">Usage</div>
        <div class="info-grid">
          <div class="info-field">
            <span class="info-key">Total Sessions</span>
            <span class="info-val">{{ agent.session_count || 0 }}</span>
          </div>
          <div class="info-field">
            <span class="info-key">Total Tokens</span>
            <span class="info-val">{{ (agent.tokens_used || 0).toLocaleString() }}</span>
          </div>
        </div>
      </section>

      <!-- Git -->
      <section v-if="agent.git_repo">
        <div class="section-label">Git</div>
        <div class="info-grid">
          <div class="info-field">
            <span class="info-key">Repository</span>
            <span class="info-val font-mono text-[11px]">{{ agent.git_repo }}</span>
          </div>
        </div>
      </section>

      <!-- Agent Profile (memory) -->
      <section>
        <div class="section-label">Agent Memory</div>
        <div class="info-grid">
          <div class="info-field">
            <span class="info-key">Static Facts</span>
            <span class="info-val">{{ profileStaticCount }}</span>
          </div>
          <div class="info-field">
            <span class="info-key">Dynamic Memories</span>
            <span class="info-val">{{ profileDynamicCount }}</span>
          </div>
        </div>
        <div class="profile-preview-box">{{ profilePreview }}</div>
      </section>

    </template>
  </div>
</template>

<style scoped>
.info-panel {
  font-family: inherit;
}

.section-label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(255,255,255,0.25);
  margin-bottom: 10px;
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.info-field {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.info-key {
  font-size: 10.5px;
  font-weight: 500;
  color: rgba(255,255,255,0.3);
}

.info-val {
  font-size: 13px;
  color: rgba(255,255,255,0.7);
  font-weight: 500;
}

.chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.chip {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 10.5px;
  font-weight: 500;
}

.chip-tool {
  background: rgba(157,213,34,0.08);
  border: 1px solid rgba(157,213,34,0.15);
  color: rgba(129,140,248,0.8);
}

.chip-skill {
  background: rgba(34,197,94,0.08);
  border: 1px solid rgba(34,197,94,0.15);
  color: rgba(74,222,128,0.7);
}

.chip-ext {
  background: rgba(168,85,247,0.08);
  border: 1px solid rgba(168,85,247,0.15);
  color: rgba(192,132,252,0.7);
}

.profile-preview-box {
  margin-top: 8px;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.06);
  font-size: 10px;
  color: rgba(255,255,255,0.3);
  font-family: 'JetBrains Mono', Menlo, 'Courier New', monospace;
  line-height: 1.6;
  max-height: 160px;
  overflow-y: auto;
  white-space: pre-wrap;
}

/* Skeleton */
.skeleton-card {
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.04);
  border-radius: 12px;
  padding: 16px;
}
.skeleton-line {
  background: rgba(255,255,255,0.04);
  border-radius: 4px;
  animation: skeletonShimmer 1.5s ease-in-out infinite;
}
@keyframes skeletonShimmer {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 0.1; }
}

.btn-retry {
  background: rgba(157,213,34,0.1);
  border: 1px solid rgba(157,213,34,0.2);
  color: #9DD522;
  font-size: 12px;
  font-weight: 500;
  padding: 6px 16px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-retry:hover {
  background: rgba(157,213,34,0.15);
}
</style>
