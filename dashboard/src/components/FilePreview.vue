<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  content: string
  filename: string
  truncatedLines?: number
  truncatedBytes?: number
  base64Content?: string
  mime?: string
  previewType?: 'text' | 'image'
}>()

const ext = computed(() => {
  const parts = props.filename.split('.')
  return parts.length > 1 ? parts.pop()!.toLowerCase() : ''
})

const langClass = computed(() => {
  const map: Record<string, string> = {
    py: 'python', js: 'javascript', ts: 'typescript', jsx: 'jsx', tsx: 'tsx',
    vue: 'vue', json: 'json', yaml: 'yaml', yml: 'yaml', md: 'markdown',
    html: 'html', css: 'css', scss: 'scss', sh: 'bash', bash: 'bash',
    env: 'dotenv', toml: 'toml', ini: 'ini', xml: 'xml', sql: 'sql',
    lock: 'json', svg: 'xml',
  }
  return map[ext.value] || ''
})

// Simple syntax highlighting — split into tokens and color them
function highlightLine(line: string): string {
  // Escape HTML
  let escaped = line
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  if (['py', 'js', 'ts', 'jsx', 'tsx', 'vue'].includes(ext.value)) {
    // Comments
    escaped = escaped.replace(/(\/\/.*$|#.*$)/g, '<span class="syn-comment">$1</span>')
    // Strings
    escaped = escaped.replace(/(&quot;[^&quot;]*&quot;|'[^']*'|`[^`]*`)/g, '<span class="syn-string">$1</span>')
    // Keywords
    const keywords = /\b(async|await|const|let|var|function|return|import|export|from|class|new|if|else|for|while|try|catch|throw|def|in|of|true|false|null|undefined|this|super|type|interface|enum|extends|implements)\b/g
    escaped = escaped.replace(keywords, '<span class="syn-keyword">$1</span>')
    // Numbers
    escaped = escaped.replace(/\b(\d+\.?\d*)\b/g, '<span class="syn-number">$1</span>')
  } else if (['json', 'yaml', 'yml', 'toml'].includes(ext.value)) {
    // Keys
    escaped = escaped.replace(/^(\s*["']?[\w.-]+["']?\s*[:=]\s*)/gm, '<span class="syn-key">$1</span>')
    // Strings
    escaped = escaped.replace(/(&quot;[^&quot;]*&quot;)/g, '<span class="syn-string">$1</span>')
    // Comments
    escaped = escaped.replace(/(#.*$|<!--.*-->)/g, '<span class="syn-comment">$1</span>')
    // Booleans/nulls
    escaped = escaped.replace(/\b(true|false|null|~)\b/g, '<span class="syn-keyword">$1</span>')
  } else if (ext.value === 'md') {
    escaped = escaped.replace(/(#+.*)/g, '<span class="syn-keyword">$1</span>')
    escaped = escaped.replace(/(`[^`]+`)/g, '<span class="syn-string">$1</span>')
  } else if (ext.value === 'bash') {
    escaped = escaped.replace(/(#.*$)/g, '<span class="syn-comment">$1</span>')
    escaped = escaped.replace(/("([^"]*)")/g, '<span class="syn-string">$1</span>')
  }

  return escaped
}

const lines = computed(() => {
  if (props.previewType === 'image') return []
  return props.content.split('\n')
})
</script>

<template>
  <div class="file-preview">
    <!-- Image preview -->
    <div v-if="previewType === 'image' && base64Content" class="image-preview">
      <img :src="`data:${mime};base64,${base64Content}`" :alt="filename" class="preview-image" />
    </div>

    <!-- Text preview -->
    <div v-else class="text-preview">
      <div class="preview-header">
        <span class="preview-lang">{{ langClass || ext || 'txt' }}</span>
        <span class="preview-info">{{ lines.length }} lines</span>
      </div>
      <div class="preview-content">
        <div v-for="(line, i) in lines" :key="i" class="preview-line">
          <span class="line-num">{{ i + 1 }}</span>
          <span class="line-text" v-html="highlightLine(line)" />
        </div>
        <div v-if="truncatedLines && truncatedLines > 0" class="preview-truncated">
          … {{ truncatedLines }} more lines
          <span v-if="truncatedBytes">({{ (truncatedBytes / 1024).toFixed(0) }} KB)</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.file-preview {
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 10px;
  overflow: hidden;
  background: rgba(0,0,0,0.2);
}

.image-preview {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  min-height: 100px;
}

.preview-image {
  max-width: 100%;
  max-height: 400px;
  border-radius: 6px;
  object-fit: contain;
}

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  background: rgba(255,255,255,0.02);
  border-bottom: 1px solid rgba(255,255,255,0.04);
  font-size: 10px;
}

.preview-lang {
  font-family: 'JetBrains Mono', Menlo, monospace;
  color: rgba(255,255,255,0.35);
  text-transform: uppercase;
  font-weight: 600;
  letter-spacing: 0.06em;
}

.preview-info {
  color: rgba(255,255,255,0.25);
}

.preview-content {
  padding: 4px 0;
  overflow-x: auto;
  max-height: 400px;
  overflow-y: auto;
}

.preview-line {
  display: flex;
  align-items: flex-start;
  padding: 0 12px;
  min-height: 20px;
  line-height: 20px;
}

.preview-line:hover {
  background: rgba(255,255,255,0.02);
}

.line-num {
  width: 36px;
  flex-shrink: 0;
  text-align: right;
  padding-right: 12px;
  font-size: 10px;
  color: rgba(255,255,255,0.2);
  font-family: 'JetBrains Mono', Menlo, monospace;
  user-select: none;
}

.line-text {
  font-family: 'JetBrains Mono', Menlo, monospace;
  font-size: 12px;
  color: rgba(255,255,255,0.65);
  white-space: pre;
  word-break: break-all;
}

.preview-truncated {
  padding: 8px 12px;
  font-size: 11px;
  color: rgba(255,255,255,0.3);
  background: rgba(245,158,11,0.06);
  border-top: 1px solid rgba(245,158,11,0.1);
  text-align: center;
}

/* Syntax colors */
:deep(.syn-comment) { color: rgba(255,255,255,0.25); font-style: italic; }
:deep(.syn-string) { color: #22C55E; }
:deep(.syn-keyword) { color: #9DD522; font-weight: 500; }
:deep(.syn-number) { color: #F59E0B; }
:deep(.syn-key) { color: #22D3EE; }

/* Scrollbar */
.preview-content::-webkit-scrollbar { width: 4px; height: 4px; }
.preview-content::-webkit-scrollbar-track { background: transparent; }
.preview-content::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.06); border-radius: 2px; }
</style>
