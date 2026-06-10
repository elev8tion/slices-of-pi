<script setup lang="ts">
import { onMounted, ref } from 'vue'
import NavIsland from '@/components/NavIsland.vue'
import Sidebar from '@/components/Sidebar.vue'
import { useAppStore } from '@/stores/app'

interface Member {
  name: string
  description: string
  tools: string[]
  model: string
}

interface Team {
  name: string
  members: Member[]
  count: number
}

const store = useAppStore()
const teams = ref<Team[]>([])
const loading = ref(true)
const deploying = ref<string | null>(null)
const deployResult = ref<string>('')

onMounted(async () => {
  await loadTeams()
})

async function loadTeams() {
  try {
    const res = await fetch('/api/teams')
    const data = await res.json()
    teams.value = data.teams || []
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function deployTeam(name: string) {
  deploying.value = name
  deployResult.value = ''
  try {
    const res = await fetch(`/api/teams/${name}/deploy`, { method: 'POST' })
    const data = await res.json()
    deployResult.value = `Deployed ${data.count} agents`
    store.fetchAgents()
  } catch (e: any) {
    deployResult.value = `Error: ${e.message}`
  } finally {
    deploying.value = null
  }
}
</script>

<template>
  <NavIsland />
  <div class="dashboard">
    <Sidebar />
    <main class="main">
      <div class="dash-header">
        <div class="dash-title">
          <h1>Teams</h1>
          <p>{{ teams.length }} rosters from ~/.pi/agents/teams.yaml</p>
        </div>
      </div>

      <div v-if="loading" class="card p-8 text-center text-text-tertiary text-sm">Loading...</div>

      <div v-else-if="teams.length === 0" class="card p-8 text-center text-text-tertiary text-sm">
        No teams defined. Create ~/.pi/agents/teams.yaml
      </div>

      <div v-else class="grid grid-cols-2 gap-3">
        <div v-for="team in teams" :key="team.name" class="card p-5 hover:border-accent/20 transition-colors">
          <div class="flex items-center justify-between mb-3">
            <h3 class="font-display text-sm font-semibold text-text-primary">{{ team.name }}</h3>
            <span class="text-[10px] text-text-muted">{{ team.count }} agents</span>
          </div>
          <div class="flex flex-wrap gap-1 mb-3">
            <span v-for="m in team.members" :key="m.name" class="text-[10px] font-medium px-1.5 py-0.5 rounded bg-accent/8 text-accent/60">{{ m.name }}</span>
          </div>
          <button
            @click="deployTeam(team.name)"
            :disabled="deploying === team.name"
            class="w-full py-1.5 rounded-btn text-xs font-medium transition-all"
            :class="deploying === team.name
              ? 'bg-white/4 text-text-tertiary'
              : 'bg-accent/10 text-accent border border-accent/20 hover:bg-accent/20'"
          >
            {{ deploying === team.name ? 'Deploying...' : 'Deploy Team' }}
          </button>
          <div v-if="deployResult" class="text-[10px] text-success mt-2">{{ deployResult }}</div>
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
