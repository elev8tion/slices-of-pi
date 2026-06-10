<script setup lang="ts">
import type { Agent } from '@/stores/app'
import { ref } from 'vue'

defineProps<{ agents: Agent[] }>()

const activeTab = ref('alerts')
</script>

<template>
  <div class="card p-[18px]">
    <div class="flex items-center justify-between mb-3">
      <h3 class="text-[13px] font-semibold text-text-secondary">Operations Queue</h3>
    </div>
    <div class="flex gap-0.5 mb-3 bg-white/3 p-[3px] rounded-btn">
      <button
        v-for="tab in ['alerts', 'running', 'recent']"
        :key="tab"
        class="px-3.5 py-1.5 rounded-[10px] text-[11.5px] font-medium transition-all capitalize"
        :class="activeTab === tab ? 'bg-white/6 text-text-primary' : 'text-text-tertiary hover:text-text-secondary'"
        @click="activeTab = tab"
      >
        {{ tab }}
      </button>
    </div>
    <div v-if="agents.filter(a => a.status === 'error').length === 0 && agents.filter(a => a.status === 'busy').length === 0" class="text-xs text-text-tertiary py-4 text-center">
      All clear — no items in queue
    </div>
    <div v-for="agent in agents.filter(a => a.status === 'error' || a.status === 'busy')" :key="agent.id" class="flex items-center gap-2.5 py-2 border-b border-white/3 last:border-b-0">
      <div class="w-1 h-7 rounded-full shrink-0" :class="agent.status === 'error' ? 'bg-danger' : 'bg-warning'" />
      <span class="text-xs font-semibold text-text-secondary">{{ agent.name }}</span>
      <span class="text-[11.5px] text-text-tertiary flex-1">{{ agent.status === 'error' ? 'Error state' : 'Currently busy' }}</span>
      <span class="text-[10px] text-text-muted whitespace-nowrap">{{ agent.status }}</span>
    </div>
  </div>
</template>
