<script setup lang="ts">
import NavIsland from './NavIsland.vue'
import Sidebar from './Sidebar.vue'

withDefaults(defineProps<{
  /** Hide sidebar (e.g. focused tools) */
  hideSidebar?: boolean
  /** Constrain main column (default true) */
  constrain?: boolean
}>(), {
  hideSidebar: false,
  constrain: true,
})
</script>

<template>
  <NavIsland />
  <div class="app-shell" :class="{ 'app-shell--wide': !constrain }">
    <Sidebar v-if="!hideSidebar" />
    <main class="app-shell-main">
      <slot />
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  gap: 0;
  padding: 24px 32px 32px;
  margin-top: 8px;
  max-width: 1440px;
  margin-left: auto;
  margin-right: auto;
}
.app-shell--wide {
  max-width: none;
}
.app-shell-main {
  flex: 1;
  min-width: 0;
}
@media (max-width: 968px) {
  .app-shell {
    padding: 16px;
  }
}
</style>
