<script setup lang="ts">
/**
 * General Flixz — operator tool on the main app surface.
 * Uses system-level /api/flixz/* (not tied to any agent).
 * Per-agent Flixz remains on AgentDetail; Console tab remains a secondary entry.
 */
import NavIsland from '@/components/NavIsland.vue'
import Sidebar from '@/components/Sidebar.vue'
import SystemFlixzPanel from '@/components/SystemFlixzPanel.vue'
</script>

<template>
  <NavIsland />
  <div class="dashboard">
    <Sidebar />
    <main class="main">
      <div class="dash-header fade-up fade-up-d2">
        <div class="dash-title">
          <h1>Flixz</h1>
          <p>General frame extraction — videos → frames for analysis. No agent required.</p>
        </div>
      </div>

      <div class="flixz-shell fade-up fade-up-d3">
        <SystemFlixzPanel />
      </div>
    </main>
  </div>
</template>

<style scoped>
.dashboard {
  display: flex;
  gap: 0;
  padding: 24px 32px 32px;
  margin-top: 8px;
  max-width: 1440px;
  margin-left: auto;
  margin-right: auto;
}
.main {
  flex: 1;
  min-width: 0;
}
.dash-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.dash-title h1 {
  font-family: 'Clash Display', sans-serif;
  font-size: 26px;
  font-weight: 600;
  letter-spacing: -0.03em;
  color: #F0F0F2;
}
.dash-title p {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.3);
  font-weight: 500;
  margin-top: 2px;
}
.flixz-shell {
  background: rgba(18, 26, 17, 0.55);
  border: 1px solid rgba(157, 213, 34, 0.12);
  border-radius: 14px;
  padding: 4px;
  min-height: 480px;
}
</style>
