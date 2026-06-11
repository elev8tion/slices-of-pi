<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

interface Step {
  id: string
  label: string
  description: string
  check: () => Promise<boolean> | boolean
  link?: string
}

const minimized = ref(false)
const dismissed = ref(localStorage.getItem('onboarding-dismissed') === 'true')
const completed = ref<Set<string>>(new Set(JSON.parse(localStorage.getItem('onboarding-completed') || '[]')))

const steps: Step[] = [
  {
    id: 'create-agent',
    label: 'Create your first agent',
    description: 'Name it, pick a model, and deploy it',
    check: async () => {
      try {
        const res = await fetch('/api/agents')
        const agents = await res.json()
        return agents.length > 0
      } catch { return false }
    },
    link: '/agents',
  },
  {
    id: 'chat',
    label: 'Send a message',
    description: 'Click an agent card and type in the Chat tab',
    check: async () => {
      try {
        const res = await fetch('/api/sessions')
        const sessions = await res.json()
        return sessions.length > 0
      } catch { return false }
    },
  },
  {
    id: 'tag',
    label: 'Tag an agent',
    description: 'Add labels to organize your agents',
    check: async () => {
      try {
        const res = await fetch('/api/tags')
        const data = await res.json()
        return data.tags?.length > 0
      } catch { return false }
    },
  },
  {
    id: 'console',
    label: 'Open the System Console',
    description: 'Watch live orchestrator logs',
    check: () => localStorage.getItem('console-visited') === 'true',
    link: '/console',
  },
  {
    id: 'replay',
    label: 'Explore Session Replay',
    description: 'See your session timeline',
    check: () => localStorage.getItem('replay-visited') === 'true',
    link: '/replay',
  },
]

const progress = computed(() => {
  const completed_count = steps.filter(s => completed.value.has(s.id)).length
  return { completed: completed_count, total: steps.length }
})

const allDone = computed(() => progress.value.completed === progress.value.total)

async function refreshProgress() {
  for (const step of steps) {
    if (completed.value.has(step.id)) continue
    try {
      const done = await step.check()
      if (done) {
        completed.value.add(step.id)
        localStorage.setItem('onboarding-completed', JSON.stringify([...completed.value]))
      }
    } catch { /* skip */ }
  }
}

function dismiss() {
  dismissed.value = true
  localStorage.setItem('onboarding-dismissed', 'true')
}

function restore() {
  dismissed.value = false
  localStorage.removeItem('onboarding-dismissed')
}

onMounted(() => {
  refreshProgress()
  // Re-check every 10s
  setInterval(refreshProgress, 10000)
})
</script>

<template>
  <!-- Restore button when dismissed -->
  <button
    v-if="dismissed"
    class="onboarding-restore"
    @click="restore"
    title="Show Getting Started"
  >
    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
    </svg>
  </button>

  <Transition name="slide-up">
    <div v-if="!dismissed" class="onboarding">
      <!-- Header -->
      <div class="onboarding-header" @click="minimized = !minimized">
        <div class="flex items-center gap-2">
          <svg class="w-4 h-4 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          <span class="text-sm font-semibold">Getting Started</span>
        </div>
        <div class="flex items-center gap-2">
          <span v-if="allDone" class="text-xs text-success">🎉 Complete!</span>
          <span v-else class="text-xs text-text-tertiary">{{ progress.completed }}/{{ progress.total }}</span>
          <button class="onboarding-close" @click.stop="dismiss" title="Dismiss">✕</button>
        </div>
      </div>

      <!-- Steps -->
      <Transition name="slide-down">
        <div v-if="!minimized" class="onboarding-steps">
          <div
            v-for="step in steps"
            :key="step.id"
            class="onboarding-step"
            :class="{ done: completed.has(step.id) }"
          >
            <div class="step-indicator">
              <div v-if="completed.has(step.id)" class="step-check">✓</div>
              <div v-else class="step-ring" />
            </div>
            <div class="step-content">
              <div class="step-label">{{ step.label }}</div>
              <div class="step-desc">{{ step.description }}</div>
            </div>
            <router-link
              v-if="step.link && !completed.has(step.id)"
              :to="step.link"
              class="step-go"
            >
              Go
            </router-link>
          </div>
        </div>
      </Transition>
    </div>
  </Transition>
</template>

<style scoped>
.onboarding-restore {
  position: fixed;
  bottom: 16px;
  right: 16px;
  z-index: 100;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: rgba(157,213,34,0.15);
  border: 1px solid rgba(157,213,34,0.3);
  color: #9DD522;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}
.onboarding-restore:hover {
  background: rgba(157,213,34,0.25);
}
.onboarding {
  position: fixed;
  bottom: 16px;
  right: 16px;
  z-index: 100;
  width: 300px;
  background: #14141A;
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 12px 40px rgba(0,0,0,0.5);
}
.onboarding-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  cursor: pointer;
  transition: background 0.15s;
}
.onboarding-header:hover {
  background: rgba(255,255,255,0.02);
}
.onboarding-close {
  background: none;
  border: none;
  color: rgba(255,255,255,0.3);
  font-size: 14px;
  cursor: pointer;
  padding: 2px 4px;
}
.onboarding-close:hover {
  color: rgba(255,255,255,0.6);
}
.onboarding-steps {
  padding: 0 14px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.onboarding-step {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  border-radius: 10px;
  transition: background 0.15s;
}
.onboarding-step:hover {
  background: rgba(255,255,255,0.02);
}
.onboarding-step.done {
  opacity: 0.5;
}
.step-indicator {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.step-check {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #22C55E;
  color: #fff;
  font-size: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.step-ring {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid rgba(255,255,255,0.15);
}
.step-content {
  flex: 1;
  min-width: 0;
}
.step-label {
  font-size: 12px;
  font-weight: 500;
  color: rgba(255,255,255,0.7);
}
.step-desc {
  font-size: 10px;
  color: rgba(255,255,255,0.3);
  margin-top: 1px;
}
.step-go {
  padding: 3px 10px;
  border-radius: 6px;
  background: rgba(157,213,34,0.1);
  color: #9DD522;
  font-size: 10px;
  text-decoration: none;
  font-weight: 500;
}
.step-go:hover {
  background: rgba(157,213,34,0.18);
}
.slide-up-enter-active, .slide-up-leave-active { transition: all 0.3s ease; }
.slide-up-enter-from, .slide-up-leave-to { transform: translateY(16px); opacity: 0; }
.slide-down-enter-active, .slide-down-leave-active { transition: all 0.2s ease; }
.slide-down-enter-from, .slide-down-leave-to { transform: translateY(-8px); opacity: 0; }
</style>
