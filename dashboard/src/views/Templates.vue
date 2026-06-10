<script setup lang="ts">
import { onMounted, ref } from 'vue'
import NavIsland from '@/components/NavIsland.vue'
import Sidebar from '@/components/Sidebar.vue'

interface Template {
  name: string
  description: string
  tools: string[]
  model?: string
  skills: string[]
  extensions: string[]
  schedule?: string
  path: string
}

const templates = ref<Template[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await fetch('/api/templates')
    const data = await res.json()
    templates.value = data.templates || []
  } catch (e) {
    console.error('Failed to load templates', e)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <NavIsland />
  <div class="dashboard">
    <Sidebar />
    <main class="main">
      <div class="dash-header">
        <div class="dash-title">
          <h1>Templates</h1>
          <p>{{ templates.length }} agent personas available</p>
        </div>
      </div>

      <div v-if="loading" class="card p-8 text-center text-text-tertiary text-sm">Loading...</div>

      <div v-else-if="templates.length === 0" class="card p-8 text-center text-text-tertiary text-sm">
        No personas found in ~/.pi/agents/
      </div>

      <div v-else class="grid grid-cols-2 gap-3">
        <div v-for="tpl in templates" :key="tpl.name" class="card p-5 hover:border-accent/20 transition-colors">
          <h3 class="font-semibold text-sm text-text-primary mb-1">{{ tpl.name }}</h3>
          <p class="text-xs text-text-tertiary leading-relaxed mb-3">{{ tpl.description || 'No description' }}</p>
          <div class="flex flex-wrap gap-1 mb-2">
            <span v-for="tool in tpl.tools.slice(0, 4)" :key="tool" class="text-[10px] font-medium px-1.5 py-px rounded bg-accent/8 text-accent/60">{{ tool }}</span>
            <span v-if="tpl.tools.length > 4" class="text-[10px] text-text-muted">+{{ tpl.tools.length - 4 }}</span>
          </div>
          <div class="flex items-center gap-3 text-[10px] text-text-muted">
            <span v-if="tpl.model">Model: {{ tpl.model }}</span>
            <span v-if="tpl.skills.length">{{ tpl.skills.length }} skills</span>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.dashboard { display: flex; gap: 0; padding: 24px 32px 32px; margin-top: 8px; max-width: 1440px; margin-left: auto; margin-right: auto; }
.main { flex: 1; min-width: 0; }
.dash-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; }
.dash-title h1 { font-family: 'Clash Display', sans-serif; font-size: 26px; font-weight: 600; letter-spacing: -0.03em; color: #F0F0F2; }
.dash-title p { font-size: 13px; color: rgba(255,255,255,0.3); font-weight: 500; margin-top: 2px; }
</style>
