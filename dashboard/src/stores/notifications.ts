import { defineStore } from 'pinia'
import { ref } from 'vue'
import { toastBus } from '@/main'

export interface Notification {
  id: string
  type: 'info' | 'success' | 'warning' | 'error'
  title: string
  message?: string
  agent_id?: string
  timestamp: number
  read: boolean
}

export const useNotificationStore = defineStore('notifications', () => {
  const notifications = ref<Notification[]>([])
  const unreadCount = ref(0)

  function add(n: Notification) {
    notifications.value.unshift(n)
    if (!n.read) unreadCount.value++
    // Show toast for important events
    if (n.type === 'error' || n.type === 'warning') {
      toastBus[n.type]?.(n.title)
    }
    // Keep max 100
    if (notifications.value.length > 100) {
      notifications.value = notifications.value.slice(0, 100)
    }
  }

  function markRead(id: string) {
    const n = notifications.value.find(x => x.id === id)
    if (n && !n.read) {
      n.read = true
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    }
  }

  function markAllRead() {
    notifications.value.forEach(n => { n.read = true })
    unreadCount.value = 0
  }

  function clear() {
    notifications.value = []
    unreadCount.value = 0
  }

  function handleWsEvent(event: any) {
    const type = event.type || event.event
    const data = event.data || event

    switch (type) {
      case 'agent_created':
        add({
          id: `agent-created-${Date.now()}`,
          type: 'success',
          title: `Agent created: ${data.name || data.agent_id?.slice(0, 8)}`,
          agent_id: data.agent_id,
          timestamp: Date.now(),
          read: false,
        })
        break
      case 'agent_deleted':
        add({
          id: `agent-deleted-${Date.now()}`,
          type: 'info',
          title: `Agent deleted: ${data.agent_id?.slice(0, 8)}`,
          agent_id: data.agent_id,
          timestamp: Date.now(),
          read: false,
        })
        break
      case 'agent_updated':
        // Only toast if there were problems
        break
      case 'session_forked':
        add({
          id: `forked-${Date.now()}`,
          type: 'info',
          title: `Session forked for ${data.agent_id?.slice(0, 8)}`,
          agent_id: data.agent_id,
          timestamp: Date.now(),
          read: false,
        })
        break
    }
  }

  return {
    notifications,
    unreadCount,
    add,
    markRead,
    markAllRead,
    clear,
    handleWsEvent,
    // Compatible with existing WebSocket handler — (message, type) signature
    addNotification(message: string, type: Notification['type'] = 'info') {
      add({
        id: `notif-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        type,
        title: message,
        timestamp: Date.now(),
        read: false,
      })
    },
  }
})
