<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  data: (number | null)[]
  color?: string
  height?: number
}>()

const color = computed(() => props.color || '#9DD522')
const height = computed(() => props.height || 24)

const pathD = computed(() => {
  const valid = props.data.filter((v): v is number => v !== null)
  if (valid.length < 2) return ''
  const max = Math.max(...valid, 1)
  const min = Math.min(...valid, 0)
  const range = max - min || 1
  const w = 100
  const h = 100
  const points = valid.map((v, i) => {
    const x = (i / (valid.length - 1)) * w
    const y = h - ((v - min) / range) * h * 0.9 - h * 0.05
    return `${x.toFixed(1)},${y.toFixed(1)}`
  })
  return `M${points.join(' L')}`
})
</script>

<template>
  <svg
    :width="data.length * 3"
    :height="height"
    :viewBox="`0 0 100 100`"
    class="sparkline"
    preserveAspectRatio="none"
  >
    <path
      v-if="pathD"
      :d="pathD"
      :stroke="color"
      stroke-width="2"
      fill="none"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
  </svg>
</template>

<style scoped>
.sparkline {
  display: block;
  opacity: 0.6;
}
</style>
