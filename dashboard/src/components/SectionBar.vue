<script setup lang="ts">
defineProps<{ title: string }>()
</script>

<template>
  <div class="flex items-center justify-between mb-3.5">
    <h2 class="font-display text-[15px] font-semibold tracking-[-0.01em] text-text-primary/85">{{ title }}</h2>
    <div class="flex items-center gap-1.5">
      <slot name="filters" />
    </div>
  </div>
</template>
