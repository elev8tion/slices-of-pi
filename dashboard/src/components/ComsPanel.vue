<script setup lang="ts">
import { ref, onMounted } from 'vue'

interface Peer {
  name: string
  project: string
  model: string
  status: string
  context_used: number
  queue_depth: number
}

const peers = ref<Peer[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await fetch('/api/coms')
    const data = await res.json()
    peers.value = data.peers || []
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="card p-[18px]">
    <div class="flex items-center justify-between mb-3">
      <h3 class="text-[13px] font-semibold text-text-secondary">Peer Pool</h3>
      <span class="text-[11px] text-text-muted font-medium">{{ peers.length }} peers</span>
    </div>

    <div v-if="loading" class="text-xs text-text-tertiary py-4 text-center">Loading...</div>

    <div v-else-if="peers.length === 0" class="text-xs text-text-tertiary py-4 text-center">
      No peers discovered. Run pi coms to connect agents.
    </div>

    <div v-else class="flex flex-col gap-1">
      <div v-for="peer in peers" :key="peer.name" class="flex items-center gap-2.5 py-2 border-b border-white/3 last:border-b-0">
        <div class="w-2 h-2 rounded-full shrink-0" :class="peer.status === 'online' ? 'bg-success' : 'bg-gray-500'" />
        <div class="flex-1 min-w-0">
          <div class="text-xs font-semibold text-text-secondary">{{ peer.name }}</div>
          <div class="text-[10px] text-text-tertiary">{{ peer.model }} · {{ peer.project }}</div>
        </div>
        <span v-if="peer.context_used" class="text-[10px] text-text-muted">{{ peer.context_used }}% ctx</span>
      </div>
    </div>
  </div>
</template>
