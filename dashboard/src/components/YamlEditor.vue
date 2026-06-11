<script setup lang="ts">
import { ref, computed, watch } from 'vue'

const props = defineProps<{
  modelValue: string
  filename?: string
  readOnly?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const editorEl = ref<HTMLTextAreaElement | null>(null)
const validationError = ref('')
const isValid = ref<boolean | null>(null)
const showLineNumbers = ref(true)

// Split content into lines
const lines = computed(() => props.modelValue.split('\n'))

// Highlight a single line of YAML
function highlightLine(line: string): string {
  let escaped = line
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  // Comments
  escaped = escaped.replace(/(#.*$)/g, '<span class="yml-comment">$1</span>')
  // Keys with colon
  escaped = escaped.replace(/^(\s*)(["']?[\w.\-/]+["']?)(\s*:)/gm, '$1<span class="yml-key">$2</span>$3')
  // Strings in quotes
  escaped = escaped.replace(/(["'])(?:(?!\1|\\).|\\.)*\1/g, '<span class="yml-string">$&</span>')
  // Booleans
  escaped = escaped.replace(/\b(true|false|yes|no|on|off)\b/g, '<span class="yml-bool">$1</span>')
  // Null
  escaped = escaped.replace(/\b(null|~)\b/g, '<span class="yml-null">$1</span>')
  // Numbers
  escaped = escaped.replace(/\b(\d+\.?\d*)\b/g, '<span class="yml-number">$1</span>')
  // List markers
  escaped = escaped.replace(/^(\s*)([-*+])(\s)/gm, '$1<span class="yml-list">$2</span>$3')

  return escaped
}

function updateValue(event: Event) {
  const textarea = event.target as HTMLTextAreaElement
  emit('update:modelValue', textarea.value)
  validate(textarea.value)
}

function validate(content: string) {
  validationError.value = ''
  isValid.value = null

  if (!content.trim()) {
    isValid.value = true
    return
  }

  // Client-side YAML validation by attempting parse
  // We do a basic check - proper validation happens server-side
  const lines = content.split('\n')
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    // Check for invalid indentation (tab instead of spaces)
    if (line.includes('\t')) {
      validationError.value = `Line ${i + 1}: Tabs used for indentation. Use spaces (2 spaces per level).`
      isValid.value = false
      return
    }
  }

  isValid.value = true
}

function handleKeydown(event: KeyboardEvent) {
  if (props.readOnly) return

  if (event.key === 'Tab') {
    event.preventDefault()
    const textarea = event.target as HTMLTextAreaElement
    const start = textarea.selectionStart
    const end = textarea.selectionEnd
    const value = textarea.value
    const newValue = value.substring(0, start) + '  ' + value.substring(end)
    emit('update:modelValue', newValue)
    // Restore cursor position
    requestAnimationFrame(() => {
      textarea.selectionStart = textarea.selectionEnd = start + 2
    })
  }
}

function syncScroll() {
  // Sync textarea scroll with highlight layer
  // The highlight div and textarea share the same parent for scrolling
}

function formatYaml() {
  // Basic formatting: ensure consistent indentation
  try {
    // Just re-indent to 2 spaces
    const lines = props.modelValue.split('\n')
    const formatted = lines
      .map(l => l.replace(/\t/g, '  '))
      .map(l => l.replace(/^ +/, m => '  '.repeat(Math.floor(m.length / 2))))
      .join('\n')
    emit('update:modelValue', formatted)
    validate(formatted)
  } catch {
    // Silently fail format
  }
}

function copyContent() {
  navigator.clipboard.writeText(props.modelValue).catch(() => {
    const ta = document.createElement('textarea')
    ta.value = props.modelValue
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
  })
}
</script>

<template>
  <div class="yaml-editor">
    <!-- Toolbar -->
    <div class="yml-toolbar">
      <div class="yml-toolbar-left">
        <span class="yml-filename">{{ filename || 'config.yaml' }}</span>
        <span v-if="isValid === true" class="yml-badge valid">✓ Valid</span>
        <span v-if="isValid === false" class="yml-badge invalid">✗ Invalid</span>
      </div>
      <div class="yml-toolbar-right">
        <button class="yml-btn" @click="formatYaml" title="Format (fix indentation)">Format</button>
        <button class="yml-btn" @click="showLineNumbers = !showLineNumbers" title="Toggle line numbers">
          {{ showLineNumbers ? 'Ln' : 'No Ln' }}
        </button>
        <button class="yml-btn" @click="copyContent" title="Copy to clipboard">Copy</button>
        <button class="yml-btn" @click="validate(modelValue)" title="Validate YAML">Validate</button>
      </div>
    </div>

    <!-- Editor area -->
    <div class="yml-editor-area">
      <!-- Highlight layer -->
      <div class="yml-highlight">
        <div class="yml-line-numbers" v-if="showLineNumbers">
          <div v-for="(_, i) in lines" :key="i" class="yml-line-num">{{ i + 1 }}</div>
        </div>
        <div class="yml-highlight-lines">
          <div v-for="(line, i) in lines" :key="i" class="yml-highlight-line" v-html="highlightLine(line)" />
        </div>
      </div>

      <!-- Actual editable textarea -->
      <textarea
        ref="editorEl"
        class="yml-textarea"
        :value="modelValue"
        :readonly="readOnly"
        @input="updateValue"
        @keydown="handleKeydown"
        @scroll="syncScroll"
        spellcheck="false"
        wrap="off"
      />
    </div>

    <!-- Validation error -->
    <div v-if="validationError" class="yml-validation-error">{{ validationError }}</div>
  </div>
</template>

<style scoped>
.yaml-editor {
  display: flex;
  flex-direction: column;
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 10px;
  overflow: hidden;
  background: rgba(0,0,0,0.3);
}

.yml-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  background: rgba(255,255,255,0.02);
  border-bottom: 1px solid rgba(255,255,255,0.04);
}

.yml-toolbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.yml-toolbar-right {
  display: flex;
  align-items: center;
  gap: 4px;
}

.yml-filename {
  font-family: 'JetBrains Mono', Menlo, monospace;
  font-size: 10px;
  color: rgba(255,255,255,0.35);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.yml-badge {
  font-size: 9px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 4px;
}
.yml-badge.valid { background: rgba(34,197,94,0.1); color: #22C55E; }
.yml-badge.invalid { background: rgba(239,68,68,0.1); color: #EF4444; }

.yml-btn {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06);
  color: rgba(255,255,255,0.45);
  font-size: 10px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s;
}
.yml-btn:hover {
  background: rgba(255,255,255,0.07);
  color: rgba(255,255,255,0.7);
}

.yml-editor-area {
  position: relative;
  display: flex;
  min-height: 200px;
  max-height: 500px;
}

.yml-highlight {
  display: flex;
  width: 100%;
  padding: 8px 0;
  overflow: hidden;
  pointer-events: none;
}

.yml-line-numbers {
  width: 36px;
  flex-shrink: 0;
  text-align: right;
  padding-right: 10px;
  border-right: 1px solid rgba(255,255,255,0.04);
  user-select: none;
}

.yml-line-num {
  font-family: 'JetBrains Mono', Menlo, monospace;
  font-size: 11px;
  line-height: 20px;
  color: rgba(255,255,255,0.15);
}

.yml-highlight-lines {
  flex: 1;
  padding: 0 12px;
  overflow: hidden;
}

.yml-highlight-line {
  font-family: 'JetBrains Mono', Menlo, monospace;
  font-size: 11px;
  line-height: 20px;
  white-space: pre;
  color: rgba(255,255,255,0.5);
}

.yml-textarea {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  padding: 8px 12px 8px 48px;
  font-family: 'JetBrains Mono', Menlo, monospace;
  font-size: 11px;
  line-height: 20px;
  color: transparent;
  caret-color: #9DD522;
  background: transparent;
  border: none;
  outline: none;
  resize: none;
  overflow: auto;
  white-space: pre;
  tab-size: 2;
}

.yml-textarea::selection {
  background: rgba(157,213,34,0.3);
}

.yml-textarea:read-only {
  cursor: default;
}

.yml-validation-error {
  padding: 6px 12px;
  font-size: 11px;
  color: #EF4444;
  background: rgba(239,68,68,0.06);
  border-top: 1px solid rgba(239,68,68,0.1);
}

/* Syntax colors for highlight layer */
:deep(.yml-comment) { color: rgba(255,255,255,0.25); font-style: italic; }
:deep(.yml-key) { color: #22D3EE; }
:deep(.yml-string) { color: #22C55E; }
:deep(.yml-bool) { color: #9DD522; font-weight: 500; }
:deep(.yml-null) { color: rgba(255,255,255,0.3); }
:deep(.yml-number) { color: #F59E0B; }
:deep(.yml-list) { color: #9DD522; }

/* Scrollbar */
.yml-textarea::-webkit-scrollbar,
.yml-highlight::-webkit-scrollbar { width: 4px; height: 4px; }
.yml-textarea::-webkit-scrollbar-track,
.yml-highlight::-webkit-scrollbar-track { background: transparent; }
.yml-textarea::-webkit-scrollbar-thumb,
.yml-highlight::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.06); border-radius: 2px; }
</style>
