<script setup lang="ts">
import { computed } from 'vue'
import type { Agent } from '@/stores/app'

const props = defineProps<{ agent: Agent }>()

const avatarColors: Record<string, string> = {
  idle: 'bg-accent/15 text-[#818CF8]',
  busy: 'bg-amber-500/15 text-amber-400',
  running: 'bg-cyan-500/15 text-cyan-400',
  error: 'bg-red-500/15 text-red-400',
  stopped: 'bg-gray-500/15 text-gray-400',
  created: 'bg-gray-500/15 text-gray-400',
}

const statusColors: Record<string, string> = {
  idle: 'bg-success',
  busy: 'bg-warning',
  running: 'bg-success',
  error: 'bg-danger',
  stopped: 'bg-gray-500',
  created: 'bg-gray-500',
}

const initials = computed(() => props.agent.name.slice(0, 1).toUpperCase())
const statusLabel = computed(() => props.agent.status.charAt(0).toUpperCase() + props.agent.status.slice(1))
</script>

<template>
  <div class="card p-[18px] cursor-pointer relative overflow-hidden" @click="$emit('click')">
    <div class="flex items-center justify-between mb-3">
      <div class="flex items-center gap-2.5">
        <div class="w-9 h-9 rounded-full flex items-center justify-center text-[13px] font-bold relative" :class="avatarColors[agent.status] || avatarColors.created">
          {{ initials }}
          <div class="absolute -bottom-[1px] -right-[1px] w-2.5 h-2.5 rounded-full border-2 border-void" :class="statusColors[agent.status] || statusColors.created" />
        </div>
        <div>
          <div class="text-sm font-semibold text-text-primary">{{ agent.name }}</div>
          <div class="text-[11px] text-text-tertiary font-medium">{{ agent.model }}</div>
        </div>
      </div>
    </div>
    <div class="flex gap-3.5 mt-2 pt-2.5 border-t border-white/4">
      <div class="flex flex-col gap-px">
        <span class="text-[10px] uppercase tracking-[0.06em] text-text-muted font-medium">Status</span>
        <span class="text-xs font-semibold text-text-secondary">{{ statusLabel }}</span>
      </div>
      <div class="flex flex-col gap-px">
        <span class="text-[10px] uppercase tracking-[0.06em] text-text-muted font-medium">Tokens</span>
        <span class="text-xs font-semibold text-text-secondary">{{ agent.tokens_used.toLocaleString() }}</span>
      </div>
      <div class="flex flex-col gap-px">
        <span class="text-[10px] uppercase tracking-[0.06em] text-text-muted font-medium">Sessions</span>
        <span class="text-xs font-semibold" :class="agent.session_count > 0 ? 'text-success' : 'text-text-secondary'">{{ agent.session_count }}</span>
      </div>
    </div>
    <!-- Sparkline -->
    <div class="h-7 mt-2 flex items-end gap-0.5">
      <div v-for="i in 12" :key="i" class="flex-1 rounded-t-sm bg-accent/15 transition-all" :style="{ height: `${20 + Math.random() * 60}%`, opacity: i % 3 === 0 ? 0.5 : 0.15 }" />
    </div>
    <!-- Tags -->
    <div class="flex gap-1 flex-wrap mt-2.5">
      <span class="text-[10px] font-medium px-1.5 py-px rounded-lg bg-white/4 text-text-tertiary">{{ agent.model.split('-').slice(0, 2).join('-') }}</span>
      <span v-if="agent.persona" class="text-[10px] font-medium px-1.5 py-px rounded-lg bg-accent/8 text-accent/60">{{ agent.persona }}</span>
    </div>
  </div>
</template>
