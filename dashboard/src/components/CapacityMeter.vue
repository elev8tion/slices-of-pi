<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  used: number
  total: number
  label: string
  showPercent?: boolean
}>()

const percent = computed(() => {
  if (props.total === 0) return 0
  return Math.round((props.used / props.total) * 100)
})

const barColor = computed(() => {
  if (percent.value >= 80) return '#EF4444'
  if (percent.value >= 50) return '#F59E0B'
  return '#22C55E'
})
</script>

<template>
  <div class="capacity-meter">
    <div class="capacity-bar-track">
      <div
        class="capacity-bar-fill"
        :style="{ width: percent + '%', background: barColor }"
      />
    </div>
    <div class="capacity-labels">
      <span class="capacity-label-text">{{ used }}/{{ total }} {{ label }}</span>
      <span v-if="showPercent !== false" class="capacity-percent">{{ percent }}%</span>
    </div>
  </div>
</template>

<style scoped>
.capacity-meter {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.capacity-bar-track {
  width: 100%;
  height: 6px;
  background: rgba(255,255,255,0.06);
  border-radius: 9999px;
  overflow: hidden;
}
.capacity-bar-fill {
  height: 100%;
  border-radius: 9999px;
  transition: width 0.5s ease, background 0.5s ease;
}
.capacity-labels {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.capacity-label-text {
  font-size: 11px;
  font-weight: 500;
  color: rgba(255,255,255,0.45);
}
.capacity-percent {
  font-size: 10px;
  font-weight: 600;
  color: rgba(255,255,255,0.3);
}
</style>
