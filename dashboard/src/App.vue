<script setup lang="ts">
import { ref, onMounted } from 'vue'
import ToastContainer from './components/ToastContainer.vue'
import OnboardingChecklist from './components/OnboardingChecklist.vue'
import EditorHelpPanel from './components/EditorHelpPanel.vue'
import CommandPalette from './components/CommandPalette.vue'
import { toastBus } from './main'

const toastRef = ref<InstanceType<typeof ToastContainer> | null>(null)

onMounted(() => {
  toastBus._add = (msg: string, type: string) => toastRef.value?.addToast(msg, type as any)
})
</script>

<template>
  <div class="noise-overlay" />
  <div class="relative z-[2]">
    <router-view />
  </div>
  <ToastContainer ref="toastRef" />
  <OnboardingChecklist />
  <EditorHelpPanel />
  <CommandPalette />
</template>
