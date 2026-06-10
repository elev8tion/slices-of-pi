<script setup lang="ts">
import { onMounted, ref } from 'vue'
import NavIsland from '@/components/NavIsland.vue'
import Sidebar from '@/components/Sidebar.vue'

interface Extension {
  name: string
  path: string
  source: string
}

const extensions = ref<Extension[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await fetch('/api/extensions')
    const data = await res.json()
    extensions.value = data.extensions || []
  } catch (e) {
    console.error('Failed to load extensions', e)
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
          <h1>Extensions</h1>
          <p>{{ extensions.length }} installed</p>
        </div>
      </div>

      <div v-if="loading" class="card p-8 text-center text-text-tertiary text-sm">Loading...</div>

      <div v-else-if="extensions.length === 0" class="card p-8 text-center text-text-tertiary text-sm">
        No extensions found in ~/.pi/agent/extensions/ or .pi/extensions/
      </div>

      <div v-else class="grid grid-cols-2 gap-3">
        <div v-for="ext in extensions" :key="ext.name" class="card p-5">
          <div class="flex items-center gap-2 mb-2">
            <h3 class="font-semibold text-sm text-text-primary">{{ ext.name }}</h3>
            <span class="text-[10px] font-medium px-2 py-0.5 rounded-full" :class="ext.source === 'global' ? 'bg-accent/10 text-accent/70' : 'bg-success/10 text-success/70'">
              {{ ext.source }}
            </span>
          </div>
          <code class="text-[10px] text-text-muted bg-white/4 px-2 py-0.5 rounded break-all">{{ ext.path }}</code>
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
