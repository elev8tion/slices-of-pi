<script setup lang="ts">
defineProps<{
  label: string
  value: string | number
  trend?: string
  trendDown?: boolean
  sub?: string
}>()
</script>

<template>
  <div class="card p-4">
    <div class="flex items-center justify-between mb-1.5">
      <span class="text-xs font-medium text-text-tertiary">{{ label }}</span>
      <span v-if="trend" class="text-[11px] font-semibold px-2 py-0.5 rounded-lg" :class="trendDown ? 'bg-danger/10 text-danger' : 'bg-success/10 text-success'">
        {{ trend }}
      </span>
    </div>
    <div class="text-[28px] font-semibold tracking-[-0.03em] text-text-primary leading-tight">
      {{ value }}
    </div>
    <div v-if="sub" class="text-xs text-text-muted font-medium mt-0.5">{{ sub }}</div>
  </div>
</template>
