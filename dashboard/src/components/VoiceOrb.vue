<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  state: 'idle' | 'listening' | 'processing' | 'speaking' | 'error'
  size?: number
}>()

const emit = defineEmits<{
  toggle: []
}>()

const orbSize = computed(() => props.size || 280)

const pulseCount = computed(() => props.state === 'listening' ? 3 : 0)
</script>

<template>
  <div
    class="voice-orb-wrapper"
    :style="{ width: orbSize + 'px', height: orbSize + 'px' }"
    @click="emit('toggle')"
    role="button"
    :tabindex="0"
    @keydown.space.prevent="emit('toggle')"
    @keydown.enter.prevent="emit('toggle')"
  >
    <!-- Pulse rings (listening state) -->
    <div
      v-for="i in pulseCount"
      :key="'ring-' + i"
      class="orb-pulse-ring"
      :style="{
        '--i': i,
        animationDelay: (i - 1) * 0.6 + 's',
      }"
    />

    <!-- Glow layer -->
    <div class="orb-glow" :class="'orb-glow--' + state" />

    <!-- Main orb -->
    <div class="orb-main" :class="'orb-main--' + state">
      <div class="orb-core" :class="'orb-core--' + state">

        <!-- Idle: microphone icon -->
        <svg v-if="state === 'idle'" class="orb-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <rect x="9" y="2" width="6" height="11" rx="3" />
          <path d="M5 10a7 7 0 0 0 14 0" />
          <line x1="12" y1="19" x2="12" y2="22" />
          <line x1="8" y1="22" x2="16" y2="22" />
        </svg>

        <!-- Listening: waveform bars -->
        <svg v-else-if="state === 'listening'" class="orb-icon orb-icon--listening" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <rect x="6" y="10" width="3" height="8" rx="1" class="wave-bar bar-1" />
          <rect x="10.5" y="6" width="3" height="16" rx="1" class="wave-bar bar-2" />
          <rect x="15" y="8" width="3" height="12" rx="1" class="wave-bar bar-3" />
          <rect x="19.5" y="11" width="3" height="6" rx="1" class="wave-bar bar-4" />
        </svg>

        <!-- Processing: spinner -->
        <svg v-else-if="state === 'processing'" class="orb-icon orb-icon--spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
        </svg>

        <!-- Speaking: sound waves -->
        <svg v-else-if="state === 'speaking'" class="orb-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M11 5L6 9H2v6h4l5 4V5z" />
          <path d="M19.07 4.93a10 10 0 0 1 0 14.14" class="sound-wave" />
          <path d="M15.54 8.46a5 5 0 0 1 0 7.07" class="sound-wave" />
        </svg>

        <!-- Error: exclamation -->
        <svg v-else class="orb-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
      </div>
    </div>
  </div>
</template>

<style scoped>
.voice-orb-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  outline: none;
}

/* Pulse rings */
.orb-pulse-ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 2px solid rgba(99, 102, 241, 0.3);
  animation: pulse-ring 2.4s cubic-bezier(0.32, 0.72, 0, 1) infinite;
}

@keyframes pulse-ring {
  0% { transform: scale(1); opacity: 0.6; }
  50% { transform: scale(1.3); opacity: 0.15; }
  100% { transform: scale(1.6); opacity: 0; }
}

/* Glow */
.orb-glow {
  position: absolute;
  inset: -30%;
  border-radius: 50%;
  opacity: 0;
  transition: all 0.8s cubic-bezier(0.32, 0.72, 0, 1);
  filter: blur(40px);
}
.orb-glow--listening {
  opacity: 0.25;
  background: radial-gradient(circle, rgba(99, 102, 241, 0.5), rgba(168, 85, 247, 0.2));
  animation: glow-pulse 2s ease-in-out infinite;
}
.orb-glow--processing {
  opacity: 0.3;
  background: radial-gradient(circle, rgba(245, 158, 11, 0.5), rgba(239, 68, 68, 0.15));
  animation: glow-rotate 3s linear infinite;
}
.orb-glow--speaking {
  opacity: 0.25;
  background: radial-gradient(circle, rgba(34, 197, 94, 0.5), rgba(34, 197, 94, 0.1));
  animation: glow-pulse 1.5s ease-in-out infinite;
}
.orb-glow--error {
  opacity: 0.3;
  background: radial-gradient(circle, rgba(239, 68, 68, 0.5), rgba(239, 68, 68, 0.1));
}

@keyframes glow-pulse {
  0%, 100% { transform: scale(1); opacity: 0.2; }
  50% { transform: scale(1.1); opacity: 0.35; }
}
@keyframes glow-rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Main orb */
.orb-main {
  position: relative;
  width: 65%;
  height: 65%;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.6s cubic-bezier(0.32, 0.72, 0, 1);
  z-index: 2;
}

.orb-main--idle {
  background: radial-gradient(circle at 30% 30%, rgba(99, 102, 241, 0.3), rgba(99, 102, 241, 0.1));
  border: 1px solid rgba(99, 102, 241, 0.2);
  box-shadow: 0 0 30px rgba(99, 102, 241, 0.1), inset 0 0 30px rgba(99, 102, 241, 0.05);
}

.orb-main--listening {
  background: radial-gradient(circle at 30% 30%, rgba(99, 102, 241, 0.5), rgba(168, 85, 247, 0.25));
  border: 1px solid rgba(99, 102, 241, 0.3);
  box-shadow: 0 0 60px rgba(99, 102, 241, 0.2), inset 0 0 40px rgba(168, 85, 247, 0.1);
  animation: orb-breathe 2s ease-in-out infinite;
}

.orb-main--processing {
  background: radial-gradient(circle at 30% 30%, rgba(245, 158, 11, 0.4), rgba(239, 68, 68, 0.15));
  border: 1px solid rgba(245, 158, 11, 0.25);
  box-shadow: 0 0 50px rgba(245, 158, 11, 0.15), inset 0 0 40px rgba(239, 68, 68, 0.08);
  animation: orb-spin 3s linear infinite;
}

.orb-main--speaking {
  background: radial-gradient(circle at 30% 30%, rgba(34, 197, 94, 0.4), rgba(34, 197, 94, 0.15));
  border: 1px solid rgba(34, 197, 94, 0.25);
  box-shadow: 0 0 50px rgba(34, 197, 94, 0.15), inset 0 0 40px rgba(34, 197, 94, 0.08);
  animation: orb-breathe 1.2s ease-in-out infinite;
}

.orb-main--error {
  background: radial-gradient(circle at 30% 30%, rgba(239, 68, 68, 0.4), rgba(239, 68, 68, 0.15));
  border: 1px solid rgba(239, 68, 68, 0.3);
  box-shadow: 0 0 50px rgba(239, 68, 68, 0.2), inset 0 0 30px rgba(239, 68, 68, 0.1);
  animation: orb-shake 0.3s ease-in-out 3;
}

@keyframes orb-breathe {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}
@keyframes orb-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
@keyframes orb-shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-4px); }
  75% { transform: translateX(4px); }
}

/* Core icon area */
.orb-core {
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.4s ease;
}

.orb-icon {
  width: 40%;
  height: 40%;
  opacity: 0.7;
}

.orb-icon--spin {
  animation: icon-spin 1.5s linear infinite;
}

@keyframes icon-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Waveform bars animation */
:deep(.wave-bar) {
  animation: wave-bounce 0.8s ease-in-out infinite alternate;
}
:deep(.bar-1) { animation-delay: 0s; }
:deep(.bar-2) { animation-delay: 0.2s; }
:deep(.bar-3) { animation-delay: 0.4s; }
:deep(.bar-4) { animation-delay: 0.6s; }

@keyframes wave-bounce {
  from { opacity: 0.4; }
  to { opacity: 1; }
}

/* Sound wave animation */
:deep(.sound-wave) {
  animation: sound-wave-pulse 1.5s ease-in-out infinite;
}
:deep(.sound-wave:last-child) {
  animation-delay: 0.5s;
}

@keyframes sound-wave-pulse {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 1; }
}
</style>
