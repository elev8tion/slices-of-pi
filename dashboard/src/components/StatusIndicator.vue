<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  status: string
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
  pulse?: boolean
}>(), {
  size: 'md',
  showLabel: false,
  pulse: false,
})

const colorMap: Record<string, string> = {
  idle: '#22C55E',
  busy: '#9DD522',
  error: '#EF4444',
  created: '#6B7280',
  stopped: '#6B7280',
  online: '#22C55E',
  offline: '#6B7280',
  connected: '#22C55E',
  disconnected: '#6B7280',
}

const sizeMap: Record<string, string> = {
  sm: '6px',
  md: '8px',
  lg: '12px',
}

const dotColor = computed(() => colorMap[props.status] || '#6B7280')
const dotSize = computed(() => sizeMap[props.size] || '8px')
const isPulsing = computed(() => props.pulse || props.status === 'busy')

const label = computed(() => props.status.charAt(0).toUpperCase() + props.status.slice(1))
</script>

<template>
  <span class="status-indicator" :class="[`size-${size}`, { pulsing: isPulsing }]">
    <span class="status-dot" :style="{ background: dotColor, width: dotSize, height: dotSize }" />
    <span v-if="showLabel" class="status-label">{{ label }}</span>
  </span>
</template>

<style scoped>
.status-indicator {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}
.status-dot {
  border-radius: 9999px;
  flex-shrink: 0;
  box-shadow: 0 0 6px var(--dot-glow, transparent);
}
.status-dot {
  --dot-glow: currentColor;
}
.pulsing .status-dot {
  animation: statusPulse 2s ease-in-out infinite;
}
.status-label {
  font-size: inherit;
  color: inherit;
  white-space: nowrap;
}

@keyframes statusPulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
</style>
