<script setup lang="ts">
import type { Activity } from '@/stores/app'

defineProps<{ activities: Activity[] }>()

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

const eventColors: Record<string, string> = {
  agent_created: 'bg-accent',
  agent_deleted: 'bg-gray-500',
  session_start: 'bg-success',
  session_end: 'bg-success',
  session_timeout: 'bg-warning',
  session_error: 'bg-danger',
}
</script>

<template>
  <div class="card p-[18px]">
    <div class="flex items-center justify-between mb-3">
      <h3 class="text-[13px] font-semibold text-text-secondary">Recent Activity</h3>
      <span class="text-[11px] text-text-muted font-medium">View all</span>
    </div>
    <div v-if="activities.length === 0" class="text-xs text-text-tertiary py-4 text-center">
      No activity yet
    </div>
    <div v-for="act in activities.slice(0, 5)" :key="act.id" class="flex gap-3 py-2.5 border-b border-white/3 last:border-b-0">
      <div class="w-2 h-2 rounded-full mt-1.5 shrink-0" :class="eventColors[act.event_type] || 'bg-accent'" />
      <div class="flex-1 min-w-0">
        <div class="text-xs text-text-secondary leading-relaxed">
          <strong class="text-text-primary font-semibold">{{ act.agent_name || act.agent_id?.slice(0, 8) }}</strong>
          {{ act.event_type.replace(/_/g, ' ') }}
        </div>
        <div class="text-[11px] text-text-muted mt-0.5">{{ timeAgo(act.created_at) }}</div>
      </div>
    </div>
  </div>
</template>
