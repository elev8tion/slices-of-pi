<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'

const show = ref(false)

function open() { show.value = true }
function close() { show.value = false }

function onKeydown(e: KeyboardEvent) {
  // ? opens help, Escape closes
  if (e.key === '?' && !e.ctrlKey && !e.metaKey && !e.altKey) {
    // Don't open if user is typing in an input
    const tag = (e.target as HTMLElement)?.tagName
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
    e.preventDefault()
    show.value = !show.value
  }
  if (e.key === 'Escape' && show.value) {
    show.value = false
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
})

defineExpose({ open, close })
</script>

<template>
  <Teleport to="body">
    <div v-if="show" class="help-overlay" @click.self="close">
      <div class="help-panel" @click.stop>
        <!-- Header -->
        <div class="help-header">
          <h2 class="help-title">Help & Shortcuts</h2>
          <button class="help-close" @click="close">✕</button>
        </div>

        <!-- Content -->
        <div class="help-body">
          <!-- Navigation -->
          <div class="help-section">
            <h3 class="help-section-title">
              <span class="help-icon">🗺️</span>
              Navigation
            </h3>
            <div class="help-items">
              <div class="help-item">
                <kbd class="help-kbd">⌘K</kbd>
                <span class="help-desc">Command palette / quick nav</span>
              </div>
              <div class="help-item">
                <kbd class="help-kbd">G</kbd>
                <span class="help-desc">then <kbd class="help-kbd">D</kbd> — go to Dashboard</span>
              </div>
              <div class="help-item">
                <kbd class="help-kbd">G</kbd>
                <span class="help-desc">then <kbd class="help-kbd">A</kbd> — go to Agents</span>
              </div>
              <div class="help-item">
                <kbd class="help-kbd">G</kbd>
                <span class="help-desc">then <kbd class="help-kbd">S</kbd> — go to Sessions</span>
              </div>
              <div class="help-item">
                <kbd class="help-kbd">G</kbd>
                <span class="help-desc">then <kbd class="help-kbd">C</kbd> — go to Console</span>
              </div>
              <div class="help-item">
                <kbd class="help-kbd">G</kbd>
                <span class="help-desc">then <kbd class="help-kbd">R</kbd> — go to Replay</span>
              </div>
            </div>
          </div>

          <!-- Chat -->
          <div class="help-section">
            <h3 class="help-section-title">
              <span class="help-icon">💬</span>
              Chat
            </h3>
            <div class="help-items">
              <div class="help-item">
                <kbd class="help-kbd">Enter</kbd>
                <span class="help-desc">Send message</span>
              </div>
              <div class="help-item">
                <kbd class="help-kbd">⇧ Enter</kbd>
                <span class="help-desc">New line (without sending)</span>
              </div>
              <div class="help-item">
                <kbd class="help-kbd">/</kbd>
                <span class="help-desc">Command mode (in chat input)</span>
              </div>
              <div class="help-item">
                <kbd class="help-kbd">↑</kbd>
                <span class="help-desc">Edit last message</span>
              </div>
              <div class="help-item">
                <kbd class="help-kbd">Esc</kbd>
                <span class="help-desc">Cancel / close panel</span>
              </div>
            </div>
          </div>

          <!-- Terminal -->
          <div class="help-section">
            <h3 class="help-section-title">
              <span class="help-icon">🖥️</span>
              Terminal
            </h3>
            <div class="help-items">
              <div class="help-item">
                <kbd class="help-kbd">Ctrl+C</kbd>
                <span class="help-desc">Interrupt / cancel command</span>
              </div>
              <div class="help-item">
                <kbd class="help-kbd">Ctrl+D</kbd>
                <span class="help-desc">Exit / end of input</span>
              </div>
              <div class="help-item">
                <kbd class="help-kbd">Tab</kbd>
                <span class="help-desc">Auto-complete</span>
              </div>
              <div class="help-item">
                <kbd class="help-kbd">↑↓</kbd>
                <span class="help-desc">Command history</span>
              </div>
              <div class="help-item">
                <kbd class="help-kbd">Ctrl+L</kbd>
                <span class="help-desc">Clear terminal</span>
              </div>
              <div class="help-item">
                <kbd class="help-kbd">Ctrl+R</kbd>
                <span class="help-desc">Reverse search history</span>
              </div>
            </div>
          </div>

          <!-- General -->
          <div class="help-section">
            <h3 class="help-section-title">
              <span class="help-icon">⚡</span>
              General
            </h3>
            <div class="help-items">
              <div class="help-item">
                <kbd class="help-kbd">?</kbd>
                <span class="help-desc">Toggle this help panel</span>
              </div>
              <div class="help-item">
                <kbd class="help-kbd">Esc</kbd>
                <span class="help-desc">Close panels / overlays</span>
              </div>
              <div class="help-item">
                <kbd class="help-kbd">Ctrl+S</kbd>
                <span class="help-desc">Save (in editors)</span>
              </div>
              <div class="help-item">
                <kbd class="help-kbd">Ctrl+F</kbd>
                <span class="help-desc">Search / find</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Footer hint -->
        <div class="help-footer">
          Press <kbd class="help-kbd">?</kbd> anywhere or <kbd class="help-kbd">Esc</kbd> to close
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.help-overlay {
  position: fixed;
  inset: 0;
  z-index: 500;
  display: flex;
  justify-content: flex-end;
  background: rgba(0,0,0,0.6);
  animation: fadeIn 0.2s ease;
}
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
.help-panel {
  width: 320px;
  height: 100vh;
  background: #0C0C10;
  border-left: 1px solid rgba(255,255,255,0.06);
  display: flex;
  flex-direction: column;
  animation: slideIn 0.3s cubic-bezier(0.32,0.72,0,1);
}
@keyframes slideIn {
  from { transform: translateX(100%); }
  to { transform: translateX(0); }
}
.help-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 20px 14px;
  border-bottom: 1px solid rgba(255,255,255,0.05);
}
.help-title {
  font-family: 'Clash Display', sans-serif;
  font-size: 16px;
  font-weight: 600;
  color: #F0F0F2;
}
.help-close {
  width: 30px;
  height: 30px;
  border-radius: 10px;
  border: 1px solid rgba(255,255,255,0.06);
  background: rgba(255,255,255,0.03);
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255,255,255,0.4);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.3s ease;
}
.help-close:hover {
  background: rgba(255,255,255,0.06);
  color: rgba(255,255,255,0.7);
}
.help-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.help-section-title {
  font-size: 13px;
  font-weight: 600;
  color: rgba(255,255,255,0.6);
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.help-icon {
  font-size: 14px;
}
.help-items {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.help-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 8px;
  border-radius: 8px;
  font-size: 12px;
  transition: background 0.2s;
}
.help-item:hover {
  background: rgba(255,255,255,0.03);
}
.help-kbd {
  font-family: 'JetBrains Mono', Menlo, monospace;
  font-size: 10px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.08);
  color: rgba(255,255,255,0.6);
  white-space: nowrap;
}
.help-desc {
  color: rgba(255,255,255,0.45);
  line-height: 1.4;
}
.help-footer {
  padding: 12px 20px;
  border-top: 1px solid rgba(255,255,255,0.05);
  font-size: 10px;
  color: rgba(255,255,255,0.25);
  text-align: center;
}
.help-footer .help-kbd {
  font-size: 9px;
}
</style>
