<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'

const store = useAppStore()
const router = useRouter()

const open = ref(false)
const query = ref('')
const activeIndex = ref(0)
const inputRef = ref<HTMLInputElement | null>(null)

interface CmdItem {
  id: string
  label: string
  hint?: string
  group: string
  run: () => void
}

const navRoutes: { path: string; label: string }[] = [
  { path: '/', label: 'Dashboard' },
  { path: '/agents', label: 'Agents' },
  { path: '/sessions', label: 'Sessions' },
  { path: '/flixz', label: 'Flixz' },
  { path: '/console', label: 'Console' },
  { path: '/replay', label: 'Replay' },
  { path: '/schedules', label: 'Schedules' },
  { path: '/skills', label: 'Skills' },
  { path: '/extensions', label: 'Extensions' },
  { path: '/templates', label: 'Templates' },
  { path: '/teams', label: 'Teams' },
  { path: '/ops', label: 'Ops' },
  { path: '/audit', label: 'Audit' },
  { path: '/settings', label: 'Settings' },
]

const items = computed<CmdItem[]>(() => {
  const list: CmdItem[] = []

  list.push({
    id: 'action-new-agent',
    label: 'Create local agent',
    hint: 'New agent',
    group: 'Actions',
    run: () => {
      store.requestNewAgent()
      router.push('/agents')
    },
  })
  list.push({
    id: 'action-ops',
    label: 'Needs attention (Ops)',
    hint: store.errorAgents ? `${store.errorAgents} error(s)` : undefined,
    group: 'Actions',
    run: () => { router.push('/ops') },
  })

  for (const r of navRoutes) {
    list.push({
      id: `nav-${r.path}`,
      label: r.label,
      hint: r.path === '/' ? 'Home' : r.path,
      group: 'Navigate',
      run: () => { router.push(r.path) },
    })
  }

  for (const a of store.agents) {
    list.push({
      id: `agent-${a.id}`,
      label: a.name,
      hint: `${a.status} · ${a.model || 'default'}`,
      group: 'Agents',
      run: () => {
        store.openAgentFromCommand(a.id, 'chat')
        if (router.currentRoute.value.path !== '/' && router.currentRoute.value.path !== '/agents') {
          router.push('/agents')
        }
      },
    })
    list.push({
      id: `agent-term-${a.id}`,
      label: `${a.name} → Terminal`,
      hint: 'Open terminal tab',
      group: 'Agents',
      run: () => {
        store.openAgentFromCommand(a.id, 'terminal')
        if (router.currentRoute.value.path !== '/' && router.currentRoute.value.path !== '/agents') {
          router.push('/agents')
        }
      },
    })
  }

  return list
})

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return items.value
  return items.value.filter(i =>
    i.label.toLowerCase().includes(q) ||
    (i.hint && i.hint.toLowerCase().includes(q)) ||
    i.group.toLowerCase().includes(q)
  )
})

const grouped = computed(() => {
  const map = new Map<string, CmdItem[]>()
  for (const item of filtered.value) {
    if (!map.has(item.group)) map.set(item.group, [])
    map.get(item.group)!.push(item)
  }
  return map
})

const flatFiltered = computed(() => filtered.value)

function openPalette() {
  open.value = true
  query.value = ''
  activeIndex.value = 0
  nextTick(() => inputRef.value?.focus())
}

function closePalette() {
  open.value = false
  query.value = ''
}

function onOpenEvent() {
  openPalette()
}

function runItem(item: CmdItem) {
  closePalette()
  item.run()
}

function onKeydown(e: KeyboardEvent) {
  const isMod = e.metaKey || e.ctrlKey
  if (isMod && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    if (open.value) closePalette()
    else openPalette()
    return
  }
  if (!open.value) return
  if (e.key === 'Escape') {
    e.preventDefault()
    closePalette()
    return
  }
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    activeIndex.value = Math.min(activeIndex.value + 1, flatFiltered.value.length - 1)
  }
  if (e.key === 'ArrowUp') {
    e.preventDefault()
    activeIndex.value = Math.max(activeIndex.value - 1, 0)
  }
  if (e.key === 'Enter') {
    e.preventDefault()
    const item = flatFiltered.value[activeIndex.value]
    if (item) runItem(item)
  }
}

watch(query, () => { activeIndex.value = 0 })
watch(open, (v) => {
  if (v && store.agents.length === 0) store.fetchAgents()
})

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  window.addEventListener('sop:open-command-palette', onOpenEvent)
})
onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
  window.removeEventListener('sop:open-command-palette', onOpenEvent)
})

defineExpose({ openPalette, closePalette })
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="cmd-overlay" @click.self="closePalette">
      <div class="cmd-panel animate-slide-up" role="dialog" aria-label="Command palette" @click.stop>
        <div class="cmd-input-row">
          <span class="cmd-kbd-hint">⌘K</span>
          <input
            ref="inputRef"
            v-model="query"
            class="cmd-input"
            placeholder="Jump to page, agent, or action…"
            autocomplete="off"
            spellcheck="false"
          />
          <button type="button" class="cmd-esc" @click="closePalette">Esc</button>
        </div>
        <div class="cmd-list">
          <template v-if="flatFiltered.length === 0">
            <div class="cmd-empty">No matches</div>
          </template>
          <template v-else>
            <div v-for="[group, groupItems] in grouped" :key="group" class="cmd-group">
              <div class="cmd-group-label">{{ group }}</div>
              <button
                v-for="item in groupItems"
                :key="item.id"
                type="button"
                class="cmd-item"
                :class="{ active: flatFiltered[activeIndex]?.id === item.id }"
                @mouseenter="activeIndex = flatFiltered.findIndex(i => i.id === item.id)"
                @click="runItem(item)"
              >
                <span class="cmd-item-label">{{ item.label }}</span>
                <span v-if="item.hint" class="cmd-item-hint">{{ item.hint }}</span>
              </button>
            </div>
          </template>
        </div>
        <div class="cmd-footer">
          <span>↑↓ navigate</span>
          <span>↵ open</span>
          <span>esc close</span>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.cmd-overlay {
  position: fixed;
  inset: 0;
  z-index: 400;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: min(20vh, 120px);
  background: rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}
.cmd-panel {
  width: min(560px, calc(100vw - 32px));
  max-height: min(70vh, 480px);
  display: flex;
  flex-direction: column;
  background: #0C0C10;
  border: 1px solid rgba(233, 236, 224, 0.1);
  border-radius: 16px;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.75);
  overflow: hidden;
}
.cmd-input-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  border-bottom: 1px solid rgba(233, 236, 224, 0.06);
}
.cmd-kbd-hint {
  font-size: 10px;
  font-weight: 600;
  color: rgba(157, 213, 34, 0.7);
  background: rgba(157, 213, 34, 0.1);
  padding: 3px 7px;
  border-radius: 6px;
  flex-shrink: 0;
}
.cmd-input {
  flex: 1;
  min-width: 0;
  background: transparent;
  border: none;
  outline: none;
  font-size: 15px;
  font-family: inherit;
  color: #E9ECE0;
}
.cmd-input::placeholder {
  color: rgba(233, 236, 224, 0.25);
}
.cmd-esc {
  font-size: 10px;
  font-weight: 600;
  color: rgba(233, 236, 224, 0.35);
  background: rgba(233, 236, 224, 0.06);
  border: none;
  border-radius: 6px;
  padding: 4px 8px;
  cursor: pointer;
  font-family: inherit;
}
.cmd-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}
.cmd-empty {
  padding: 24px;
  text-align: center;
  font-size: 13px;
  color: rgba(233, 236, 224, 0.35);
}
.cmd-group {
  margin-bottom: 8px;
}
.cmd-group-label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: rgba(233, 236, 224, 0.25);
  padding: 6px 10px 4px;
}
.cmd-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  text-align: left;
  padding: 10px 12px;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: rgba(233, 236, 224, 0.75);
  font-size: 13px;
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  transition: background 0.15s ease;
}
.cmd-item:hover,
.cmd-item.active {
  background: rgba(157, 213, 34, 0.12);
  color: #E9ECE0;
}
.cmd-item-label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cmd-item-hint {
  font-size: 11px;
  color: rgba(233, 236, 224, 0.3);
  flex-shrink: 0;
  font-family: 'JetBrains Mono', monospace;
}
.cmd-footer {
  display: flex;
  gap: 16px;
  padding: 8px 16px;
  border-top: 1px solid rgba(233, 236, 224, 0.05);
  font-size: 10px;
  color: rgba(233, 236, 224, 0.25);
}
</style>
