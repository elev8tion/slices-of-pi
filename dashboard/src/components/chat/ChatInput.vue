<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  disabled?: boolean
  placeholder?: string
  resumeMode?: boolean
}>()

const emit = defineEmits<{
  send: [text: string]
  attach: [file: File]
  'update:resumeMode': [value: boolean]
}>()

const input = ref('')

function handleSend() {
  const text = input.value.trim()
  if (!text || props.disabled) return
  emit('send', text)
  input.value = ''
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

function onFileChange(e: Event) {
  const target = e.target as HTMLInputElement
  if (target.files && target.files[0]) {
    emit('attach', target.files[0])
    target.value = ''
  }
}
</script>

<template>
  <div class="flex items-center gap-2 mx-4 mb-3">
    <!-- Resume toggle -->
    <button
      class="text-[10px] font-medium px-2 py-1 rounded-md transition-colors shrink-0"
      :class="resumeMode ? 'bg-accent/15 text-accent border border-accent/20' : 'bg-white/1 backdrop-blur-sm text-text-tertiary border border-white/10 hover:bg-white/4'"
      @click="emit('update:resumeMode', !resumeMode)"
    >{{ resumeMode ? 'Resume' : 'New' }}</button>

    <!-- Input bar -->
    <div class="flex-1 flex items-center gap-1.5 p-1.5 bg-transparent backdrop-blur-sm border border-white/10 rounded-2xl hover:border-white/15 focus-within:border-accent/30 transition-colors">
      <!-- File attach button -->
      <label class="w-7 h-7 flex items-center justify-center rounded-full text-text-tertiary hover:text-text-secondary hover:bg-white/5 cursor-pointer transition-colors shrink-0">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
        </svg>
        <input type="file" class="hidden" @change="onFileChange" />
      </label>

      <input
        v-model="input"
        :disabled="disabled"
        :placeholder="placeholder || 'Message agent...'"
        class="flex-1 bg-transparent border-none outline-none text-xs text-text-secondary placeholder:text-text-muted min-w-0"
        @keydown="onKeydown"
      />

      <!-- Send button -->
      <button
        :disabled="!input.trim() || disabled"
        class="w-7 h-7 rounded-full bg-accent flex items-center justify-center text-white text-xs disabled:opacity-30 transition-opacity shrink-0"
        @click="handleSend"
      >↑</button>
    </div>
  </div>
</template>
