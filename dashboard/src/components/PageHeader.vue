<script setup lang="ts">
defineProps<{
  title: string
  subtitle?: string
}>()
</script>

<template>
  <div class="page-header fade-up fade-up-d2">
    <div class="page-header-text">
      <h1 class="page-header-title">{{ title }}</h1>
      <p v-if="subtitle" class="page-header-sub">{{ subtitle }}</p>
      <slot name="subtitle" />
    </div>
    <div v-if="$slots.actions" class="page-header-actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}
.page-header-title {
  font-family: 'Clash Display', sans-serif;
  font-size: 26px;
  font-weight: 600;
  letter-spacing: -0.03em;
  color: #F0F0F2;
}
.page-header-sub {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.3);
  font-weight: 500;
  margin-top: 2px;
}
.page-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
