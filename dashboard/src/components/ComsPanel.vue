<script setup lang="ts">
import { ref, onMounted } from 'vue'

interface Peer {
  name: string
  project: string
  model: string
  status: string
  context_used: number
  queue_depth: number
  recent_facts: string[]
  fact_count: number
}

const peers = ref<Peer[]>([])
const loading = ref(true)
const expandedPeers = ref<Set<string>>(new Set())

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

function toggleExpand(name: string) {
  if (expandedPeers.value.has(name)) {
    expandedPeers.value.delete(name)
  } else {
    expandedPeers.value.add(name)
  }
}
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
      <div v-for="peer in peers" :key="peer.name">
        <div
          class="flex items-center gap-2.5 py-2 border-b border-white/3 cursor-pointer hover:bg-white/[0.02] transition-colors"
          :class="{ 'border-b-0': expandedPeers.has(peer.name) }"
          @click="toggleExpand(peer.name)"
        >
          <div class="w-2 h-2 rounded-full shrink-0" :class="peer.status === 'online' ? 'bg-success' : 'bg-gray-500'" />
          <div class="flex-1 min-w-0">
            <div class="text-xs font-semibold text-text-secondary">{{ peer.name }}</div>
            <div class="text-[10px] text-text-tertiary">{{ peer.model }} · {{ peer.project }}</div>
          </div>
          <span v-if="peer.fact_count" class="text-[10px] text-lime px-1.5 py-0.5 rounded bg-lime/10 font-medium">{{ peer.fact_count }} facts</span>
          <span v-if="peer.context_used" class="text-[10px] text-text-muted">{{ peer.context_used }}% ctx</span>
          <svg class="w-3 h-3 text-text-muted transition-transform" :class="{ 'rotate-180': expandedPeers.has(peer.name) }" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
        </div>
        <div v-if="expandedPeers.has(peer.name) && peer.recent_facts?.length" class="px-4 py-2 bg-white/[0.02] border-b border-white/3 rounded-b-lg">
          <div class="text-[10px] font-semibold text-text-muted mb-1 uppercase tracking-wider">Recent Facts</div>
          <div v-for="(fact, fi) in peer.recent_facts" :key="fi" class="text-[10.5px] text-text-tertiary py-1 border-b border-white/3 last:border-b-0">
            {{ fact }}
          </div>
        </div>
        <div v-else-if="expandedPeers.has(peer.name)" class="px-4 py-2 bg-white/[0.02] border-b border-white/3 rounded-b-lg">
          <div class="text-[10px] text-text-muted">No shared facts from this peer.</div>
        </div>
      </div>
    </div>
  </div>
</template>
