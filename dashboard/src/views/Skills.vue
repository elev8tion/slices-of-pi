<script setup lang="ts">
import { onMounted, ref } from 'vue'
import NavIsland from '@/components/NavIsland.vue'
import Sidebar from '@/components/Sidebar.vue'

interface Skill {
  name: string
  description: string
  location: string
}

const skills = ref<Skill[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await fetch('/api/skills')
    const data = await res.json()
    skills.value = data.skills || []
  } catch (e) {
    console.error('Failed to load skills', e)
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
          <h1>Skills</h1>
          <p>{{ skills.length }} installed</p>
        </div>
      </div>

      <div v-if="loading" class="card p-8 text-center text-text-tertiary text-sm">Loading...</div>

      <div v-else-if="skills.length === 0" class="card p-8 text-center text-text-tertiary text-sm">
        No skills found in ~/.pi/agent/skills/
      </div>

      <div v-else class="grid grid-cols-2 gap-3">
        <div v-for="skill in skills" :key="skill.name" class="card p-5">
          <h3 class="font-semibold text-sm text-text-primary mb-1">{{ skill.name }}</h3>
          <p class="text-xs text-text-tertiary leading-relaxed mb-2">{{ skill.description || 'No description' }}</p>
          <code class="text-[10px] text-text-muted bg-white/4 px-2 py-0.5 rounded">{{ skill.location }}</code>
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
