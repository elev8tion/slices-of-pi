<script setup lang="ts">
import NavIsland from '@/components/NavIsland.vue'
import Sidebar from '@/components/Sidebar.vue'
import SystemConsole from '@/components/SystemConsole.vue'
</script>

<template>
  <NavIsland />
  <div class="console-page">
    <Sidebar />
    <main class="main">
      <!-- Header -->
      <div class="console-header fade-up">
        <div class="console-title">
          <h1>System Console</h1>
          <p>Live orchestrator log stream — <code class="inline-code">~/.pi/agent/orchestrator.log</code></p>
        </div>
      </div>

      <!-- Console -->
      <div class="console-body fade-up fade-up-d2">
        <SystemConsole />
      </div>
    </main>
  </div>
</template>

<style scoped>
.console-page {
  display: flex;
  gap: 0;
  padding: 24px 32px 32px;
  margin-top: 8px;
  max-width: 1440px;
  margin-left: auto;
  margin-right: auto;
  height: calc(100vh - 60px);
}
.main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.console-header {
  margin-bottom: 16px;
}
.console-title h1 {
  font-family: 'Clash Display', sans-serif;
  font-size: 26px;
  font-weight: 600;
  letter-spacing: -0.03em;
  color: #F0F0F2;
}
.console-title p {
  font-size: 13px;
  color: rgba(255,255,255,0.3);
  font-weight: 500;
  margin-top: 2px;
}
.inline-code {
  font-family: 'JetBrains Mono', Menlo, monospace;
  font-size: 12px;
  background: rgba(255,255,255,0.04);
  padding: 1px 6px;
  border-radius: 4px;
  color: rgba(255,255,255,0.5);
}
.console-body {
  flex: 1;
  min-height: 0;
}

.fade-up {
  opacity: 0;
  transform: translateY(16px);
  animation: fadeUp 0.7s cubic-bezier(0.32,0.72,0,1) forwards;
}
.fade-up-d2 {
  animation-delay: 0.1s;
}
@keyframes fadeUp {
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 968px) {
  .console-page {
    padding: 16px;
    flex-direction: column;
  }
}
</style>
