<script setup lang="ts">
defineProps<{
  runtime?: string
  size?: 'sm' | 'md'
}>()

const sizes = {
  sm: 'text-[10px] px-1.5 py-0.5 rounded-md',
  md: 'text-xs px-2 py-1 rounded-lg',
}
</script>

<template>
  <span
    v-if="runtime === 'gemini-cli' || runtime === 'gemini'"
    :class="['inline-flex items-center gap-1 font-medium', sizes[size || 'sm']]"
    style="background: rgba(59,130,246,0.15); color: #60A5FA;"
  >
    <span class="text-[10px]">✦</span>
    <span>Gemini CLI</span>
  </span>
  <span
    v-else
    :class="['inline-flex items-center gap-1 font-medium', sizes[size || 'sm']]"
    style="background: rgba(157,213,34,0.15); color: #9DD522;"
  >
    <span class="text-[10px] font-bold">π</span>
    <span>pi-code</span>
  </span>
</template>
