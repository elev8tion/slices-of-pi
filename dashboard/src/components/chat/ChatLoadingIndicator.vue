<script setup lang="ts">
defineProps<{
  variant?: 'inline' | 'full'
}>()
</script>

<template>
  <div class="rounded-2xl rounded-bl-md px-3 py-2 bg-white/4 border border-white/5" :class="variant === 'full' ? 'text-center py-6' : ''">
    <div class="flex gap-1.5" :class="variant === 'full' ? 'justify-center' : ''">
      <span class="w-1.5 h-1.5 rounded-full bg-text-muted animate-pulse" style="animation-delay:0ms" />
      <span class="w-1.5 h-1.5 rounded-full bg-text-muted animate-pulse" style="animation-delay:200ms" />
      <span class="w-1.5 h-1.5 rounded-full bg-text-muted animate-pulse" style="animation-delay:400ms" />
    </div>
    <div v-if="variant === 'full'" class="text-[10px] text-text-muted mt-2">Thinking...</div>
  </div>
</template>
