<script setup lang="ts">
import { ref } from 'vue'

interface Toast {
  id: number
  message: string
  type: 'info' | 'success' | 'error'
}

const toasts = ref<Toast[]>([])
let nextId = 0

function addToast(message: string, type: 'info' | 'success' | 'error' = 'info') {
  const id = nextId++
  toasts.value.push({ id, message, type })
  setTimeout(() => {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }, 4000)
}

defineExpose({ addToast })
</script>

<template>
  <div class="fixed bottom-6 right-6 z-[300] flex flex-col gap-2">
    <div
      v-for="toast in toasts"
      :key="toast.id"
      class="px-4 py-2.5 rounded-btn text-xs font-medium border backdrop-blur-md shadow-lg animate-slide-up"
      :class="toast.type === 'error'
        ? 'bg-danger/10 border-danger/20 text-danger'
        : toast.type === 'success'
        ? 'bg-success/10 border-success/20 text-success'
        : 'bg-white/5 border-white/8 text-text-secondary'"
    >
      {{ toast.message }}
    </div>
  </div>
</template>

<style scoped>
.animate-slide-up {
  animation: slideUp 0.3s cubic-bezier(0.32,0.72,0,1);
}
@keyframes slideUp {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
