<script setup lang="ts">
/**
 * General Flixz — operator tool on the main app surface.
 * Uses system-level /api/flixz/* (not tied to any agent).
 */
import AppShell from '@/components/AppShell.vue'
import PageHeader from '@/components/PageHeader.vue'
import SystemFlixzPanel from '@/components/SystemFlixzPanel.vue'
</script>

<template>
  <AppShell>
    <PageHeader
      title="Flixz"
      subtitle="General frame extraction — videos → frames for analysis. No agent required."
    />
    <div class="flixz-shell fade-up fade-up-d3">
      <SystemFlixzPanel />
    </div>
  </AppShell>
</template>

<style scoped>
.flixz-shell {
  background: rgba(18, 26, 17, 0.55);
  border: 1px solid rgba(157, 213, 34, 0.12);
  border-radius: 14px;
  padding: 4px;
  min-height: 480px;
}
</style>
