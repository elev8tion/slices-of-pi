<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { computed, ref, onMounted, onUnmounted } from 'vue'
import HostTelemetry from './HostTelemetry.vue'
import StatusIndicator from './StatusIndicator.vue'
import UserMenu from './UserMenu.vue'
import { useAuthStore } from '@/stores/auth'
import VoiceWorkspace from './VoiceWorkspace.vue'

const route = useRoute()
const router = useRouter()
const store = useAppStore()

const showVoice = ref(false)
const voiceAgentId = ref('')
const voiceAgentName = ref('')
const showMore = ref(false)
const showMobileMenu = ref(false)
const mobileMoreOpen = ref(false)
let moreTimeout: ReturnType<typeof setTimeout> | null = null

function openMore() {
  if (moreTimeout) clearTimeout(moreTimeout)
  showMore.value = true
}
function scheduleClose() {
  moreTimeout = setTimeout(() => { showMore.value = false }, 200)
}
function cancelClose() {
  if (moreTimeout) { clearTimeout(moreTimeout); moreTimeout = null }
}

function openSystemVoice() {
  // System-level voice — always available, not tied to any agent
  voiceAgentId.value = '__system__'
  voiceAgentName.value = 'Slice of Pi System'
  showVoice.value = true
}

function openAgentVoice(agent: any) {
  voiceAgentId.value = agent.id
  voiceAgentName.value = agent.name
  showVoice.value = true
}

const primaryLinks = [
  { to: '/', label: 'Dashboard' },
  { to: '/agents', label: 'Agents' },
  { to: '/sessions', label: 'Sessions' },
  { to: '/console', label: 'Console' },
  { to: '/replay', label: 'Replay' },
]

const secondaryLinks = [
  { to: '/schedules', label: 'Schedules' },
  { to: '/skills', label: 'Skills' },
  { to: '/extensions', label: 'Extensions' },
  { to: '/templates', label: 'Templates' },
  { to: '/teams', label: 'Teams' },
  { to: '/ops', label: 'Ops' },
  { to: '/audit', label: 'Audit' },
  { to: '/settings', label: 'Settings' },
]

const allLinks = [...primaryLinks, ...secondaryLinks]

const activeRoute = computed(() => {
  if (route.path === '/') return '/'
  return '/' + (route.path.split('/')[1] || '')
})

const isMobile = ref(window.innerWidth < 768)
function onResize() {
  isMobile.value = window.innerWidth < 768
  if (!isMobile.value) showMobileMenu.value = false
}
onMounted(() => window.addEventListener('resize', onResize))
onUnmounted(() => window.removeEventListener('resize', onResize))

function toggleMobile() { showMobileMenu.value = !showMobileMenu.value }
function closeMobile() { showMobileMenu.value = false }
function navTo(path: string) {
  router.push(path)
  showMore.value = false
  showMobileMenu.value = false
  mobileMoreOpen.value = false
}
</script>

<template>
  <nav class="nav-island fade-up">
    <!-- Sidebar toggle -->
    <button class="sidebar-toggle-btn" @click="store.toggleSidebar()" title="Toggle sidebar">
      <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
      </svg>
    </button>

    <!-- Desktop links -->
    <div class="nav-links-desktop">
      <router-link v-for="link in primaryLinks" :key="link.to" :to="link.to"
        class="nav-link" :class="{ active: activeRoute === link.to }">
        {{ link.label }}
      </router-link>

      <!-- More dropdown -->
      <div class="nav-more-wrapper" @mouseenter="openMore" @mouseleave="scheduleClose">
        <button class="nav-link nav-more-btn"
          :class="{ active: secondaryLinks.some(l => activeRoute === l.to) }"
          @click="showMore = !showMore">
          More
          <svg class="nav-chevron" :class="{ rotated: showMore }" width="10" height="10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        <div v-if="showMore" class="nav-dropdown" @mouseenter="cancelClose" @mouseleave="scheduleClose">
          <router-link v-for="link in secondaryLinks" :key="link.to" :to="link.to"
            class="nav-dropdown-item" :class="{ active: activeRoute === link.to }"
            @click="showMore = false">
            {{ link.label }}
          </router-link>
        </div>
      </div>
    </div>

    <div class="nav-divider nav-divider-desktop" />
    <div class="nav-desktop-only"><HostTelemetry /></div>
    <div class="nav-divider nav-divider-desktop" />

    <div class="nav-divider nav-divider-desktop" />
    <div class="nav-actions">
      <UserMenu />
      <div class="nav-divider nav-divider-desktop" />
      <button class="voice-icon-btn" @click="openSystemVoice" title="System voice — talk to Slice of Pi">🎤</button>
    </div>

    <div class="nav-divider nav-divider-desktop" />
    <div class="nav-actions">
      <StatusIndicator :status="store.connected ? 'online' : 'offline'" size="md" :pulse="store.connected" />
      <span class="connection-label">{{ store.connected ? 'Connected' : 'Offline' }}</span>
    </div>

    <!-- Mobile hamburger -->
    <button class="hamburger-btn" @click="toggleMobile" aria-label="Menu">
      <span class="hamburger-line" :class="{ open: showMobileMenu }" />
      <span class="hamburger-line" :class="{ open: showMobileMenu }" />
      <span class="hamburger-line" :class="{ open: showMobileMenu }" />
    </button>
  </nav>

  <!-- Mobile menu -->
  <div v-if="showMobileMenu" class="mobile-menu-overlay" @click="closeMobile">
    <div class="mobile-menu" @click.stop>
      <div class="mobile-menu-header">
        <img src="/logo-nav.png" alt="Slice of Pi" class="mobile-logo" />
        <button class="mobile-close-btn" @click="closeMobile">✕</button>
      </div>
      <div class="mobile-links">
        <button v-for="link in allLinks" :key="link.to" class="mobile-link"
          :class="{ active: activeRoute === link.to }" @click="navTo(link.to)">
          {{ link.label }}
        </button>
      </div>
      <div class="mobile-footer">
        <HostTelemetry />
        <div class="mobile-connection">
          <StatusIndicator :status="store.connected ? 'online' : 'offline'" size="sm" :show-label="true" />
        </div>
        <button class="mobile-voice-btn" @click="closeMobile(); openSystemVoice()">
          🎤 System Voice
        </button>
        <UserMenu />
      </div>
    </div>
  </div>

  <VoiceWorkspace v-if="showVoice" :agent-id="voiceAgentId" :agent-name="voiceAgentName" @close="showVoice = false" />
</template>

<style scoped>
.nav-island {
  position: sticky; top: 12px; z-index: 100;
  margin: 0 auto; width: max-content; max-width: calc(100% - 32px);
  display: flex; align-items: center; gap: 16px;
  padding: 8px 16px 8px 12px;
  background: rgba(10,10,10,0.88);
  backdrop-filter: blur(32px) saturate(1.4);
  -webkit-backdrop-filter: blur(32px) saturate(1.4);
  border: 1px solid rgba(233,236,224,0.06);
  border-radius: 9999px;
  box-shadow: 0 0 0 1px rgba(233,236,224,0.03), 0 8px 32px rgba(0,0,0,0.6);
  transition: all 0.5s cubic-bezier(0.32,0.72,0,1);
}
.nav-island:hover {
  border-color: rgba(233,236,224,0.1);
  box-shadow: 0 0 0 1px rgba(233,236,224,0.05), 0 12px 48px rgba(0,0,0,0.7);
}

.sidebar-toggle-btn {
  display: flex; align-items: center; justify-content: center;
  background: none; border: none;
  color: rgba(233,236,224,0.45); cursor: pointer;
  padding: 6px; border-radius: 8px; transition: all 0.3s ease;
}
.sidebar-toggle-btn:hover {
  color: rgba(233,236,224,0.8); background: rgba(233,236,224,0.04);
}

.nav-links-desktop { display: flex; align-items: center; gap: 2px; }
.nav-link {
  font-size: 12.5px; font-weight: 500; letter-spacing: 0.01em;
  padding: 6px 12px; border-radius: 8px;
  color: rgba(233,236,224,0.45); text-decoration: none; white-space: nowrap;
  transition: all 0.4s cubic-bezier(0.32,0.72,0,1);
}
.nav-link:hover { color: rgba(233,236,224,0.8); background: rgba(233,236,224,0.04); }
.nav-link.active { color: #E9ECE0; background: rgba(157,213,34,0.12); }

.nav-more-wrapper { position: relative; }
.nav-more-btn {
  display: flex; align-items: center; gap: 2px;
  background: none; border: none; font-family: inherit; cursor: pointer;
}
.nav-chevron { transition: transform 0.3s ease; }
.nav-chevron.rotated { transform: rotate(180deg); }
.nav-dropdown {
  position: absolute; top: calc(100% + 8px); right: 0;
  min-width: 160px; background: rgba(10,10,10,0.95);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(233,236,224,0.1); border-radius: 12px;
  padding: 6px; box-shadow: 0 12px 48px rgba(0,0,0,0.6); z-index: 200;
}
.nav-dropdown-item {
  display: block; padding: 8px 12px; border-radius: 8px;
  font-size: 12.5px; font-weight: 500;
  color: rgba(233,236,224,0.45); text-decoration: none; transition: all 0.2s ease;
}
.nav-dropdown-item:hover { color: rgba(233,236,224,0.8); background: rgba(233,236,224,0.04); }
.nav-dropdown-item.active { color: #E9ECE0; background: rgba(157,213,34,0.12); }

.nav-divider { width: 1px; height: 20px; background: rgba(233,236,224,0.06); }
.nav-actions { display: flex; align-items: center; gap: 12px; padding-left: 4px; }
.voice-icon-btn {
  background: none; border: none; font-size: 16px; cursor: pointer;
  padding: 4px 6px; border-radius: 8px; transition: all 0.3s ease; line-height: 1;
}
.voice-icon-btn:hover { background: rgba(157,213,34,0.12); transform: scale(1.1); }
.connection-label { font-size: 11px; color: rgba(233,236,224,0.35); font-weight: 500; white-space: nowrap; }

.hamburger-btn { display: none; flex-direction: column; gap: 3px; background: none; border: none; cursor: pointer; padding: 6px; border-radius: 8px; }
.hamburger-line { display: block; width: 18px; height: 2px; background: rgba(233,236,224,0.5); border-radius: 2px; transition: all 0.3s ease; }
.hamburger-line.open:nth-child(1) { transform: rotate(45deg) translate(3.5px, 3.5px); }
.hamburger-line.open:nth-child(2) { opacity: 0; }
.hamburger-line.open:nth-child(3) { transform: rotate(-45deg) translate(3.5px, -3.5px); }

.mobile-menu-overlay { display: none; position: fixed; inset: 0; z-index: 300; background: rgba(0,0,0,0.6); backdrop-filter: blur(8px); }
.mobile-menu { position: fixed; top: 0; right: 0; width: 280px; height: 100vh; background: #0A0A0A; border-left: 1px solid rgba(233,236,224,0.06); padding: 20px; display: flex; flex-direction: column; animation: slideIn 0.3s cubic-bezier(0.32,0.72,0,1); }
@keyframes slideIn { from { transform: translateX(100%); } to { transform: translateX(0); } }
.mobile-menu-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid rgba(233,236,224,0.06); }
.mobile-logo { width: 32px; height: 32px; border-radius: 10px; }
.mobile-close-btn { background: none; border: none; color: rgba(233,236,224,0.45); font-size: 18px; cursor: pointer; padding: 4px; }
.mobile-links { flex: 1; display: flex; flex-direction: column; gap: 2px; overflow-y: auto; }
.mobile-link { display: block; width: 100%; text-align: left; padding: 10px 12px; border-radius: 10px; font-size: 14px; font-weight: 500; color: rgba(233,236,224,0.45); background: none; border: none; cursor: pointer; transition: all 0.2s ease; font-family: inherit; }
.mobile-link:hover { color: rgba(233,236,224,0.8); background: rgba(233,236,224,0.04); }
.mobile-link.active { color: #E9ECE0; background: rgba(157,213,34,0.12); }
.mobile-footer { border-top: 1px solid rgba(233,236,224,0.06); padding-top: 16px; margin-top: 16px; display: flex; flex-direction: column; gap: 12px; }
.mobile-connection { display: flex; align-items: center; gap: 8px; }
.mobile-voice-btn {
  display: flex; align-items: center; gap: 8px;
  width: 100%; text-align: left;
  padding: 10px 12px; border-radius: 10px;
  font-size: 14px; font-weight: 500;
  color: rgba(233,236,224,0.45);
  background: none; border: none; cursor: pointer;
  transition: all 0.2s ease; font-family: inherit;
}
.mobile-voice-btn:hover {
  color: rgba(233,236,224,0.8);
  background: rgba(233,236,224,0.04);
}

.nav-divider-desktop, .nav-desktop-only { display: block; }

@media (max-width: 1100px) {
  .nav-links-desktop { gap: 0; }
  .nav-link { padding: 6px 8px; font-size: 11.5px; }
  .nav-island { gap: 10px; padding: 8px 12px 8px 10px; }
  .nav-divider-desktop { display: none; }
}
@media (max-width: 768px) {
  .nav-links-desktop, .nav-divider-desktop, .nav-desktop-only, .connection-label { display: none; }
  .hamburger-btn { display: flex; }
  .mobile-menu-overlay { display: block; }
  .nav-island { width: calc(100% - 16px); padding: 8px 14px; gap: 12px; justify-content: space-between; }
}
</style>
