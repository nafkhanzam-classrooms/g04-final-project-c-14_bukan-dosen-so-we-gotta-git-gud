import { defineStore } from 'pinia'
import { ref, nextTick } from 'vue'

const STORAGE_KEY = 'classroom_session_id'

export const useClassroomStore = defineStore('classroom', () => {
  const socket = ref<WebSocket | null>(null)
  const isConnected = ref(false)
  const sessionId = ref<string | null>(null)
  const lastError = ref<string | null>(null)

  const currentSlide = ref(1)
  const totalSlides = ref(0)
  const isSlidesReady = ref(false)

  const loadSavedSession = (): string | null => localStorage.getItem(STORAGE_KEY)

  const saveSession = (id: string) => {
    sessionId.value = id
    localStorage.setItem(STORAGE_KEY, id)
  }

  const clearSession = () => {
    sessionId.value = null
    localStorage.removeItem(STORAGE_KEY)
  }

  const connect = (roomCode: string, role: 'host' | 'student', username: string = 'Anonymous') => {
    lastError.value = null
    if (socket.value?.readyState === WebSocket.OPEN) return

    const wsUrl = import.meta.env.VITE_WS_URL
    socket.value = new WebSocket(wsUrl)

    let isReconnect = false

    socket.value.onopen = () => {
      isConnected.value = true
      const savedId = loadSavedSession()
      if (savedId) {
        isReconnect = true
        socket.value?.send(JSON.stringify({ data: { session_id: savedId } }))
      } else {
        socket.value?.send(JSON.stringify({}))
      }
    }

    socket.value.onmessage = (event) => {
      const payload = JSON.parse(event.data)
      if (payload.event === 'connection:assigned') {
        saveSession(payload.data.session_id)
        if (isReconnect) {
          send('classroom:sync', {})
        } else {
          if (role === 'host') {
            send('classroom:create', { class_code: roomCode })
          } else {
            send('classroom:join', { class_code: roomCode, student_name: username })
          }
        }
        return
      }
      if (payload.event === 'connection:replaced') {
        alert('Your session was taken over by another device. You will be redirected.')
        disconnect()
        clearSession()
        window.location.href = '/'
        return
      }
      handleIncomingEvent(payload.event, payload.data)
    }

    socket.value.onclose = () => {
      isConnected.value = false
    }
  }

  const send = (event: string, data: any) => {
    if (socket.value?.readyState === WebSocket.OPEN) {
      socket.value.send(JSON.stringify({ event, data }))
    }
  }

  const handleIncomingEvent = (event: string, data: any) => {
    switch (event) {
      case 'slides:ready':
        totalSlides.value = data.total_slides
        currentSlide.value = 1
        nextTick(() => { isSlidesReady.value = true })
        break
      case 'slides:changed':
        currentSlide.value = data.slide_number
        break
      case 'classroom:state_sync':
        totalSlides.value = data.total_slides
        currentSlide.value = data.current_slide
        nextTick(() => { isSlidesReady.value = true })
        break
      case 'classroom:created':
      case 'classroom:joined':
        lastError.value = null
        send('classroom:sync', {})
        break
      case 'classroom:error':
        console.error('Classroom error:', data.message)
        lastError.value = data.message
        break
    }
  }

  const disconnect = () => {
    socket.value?.close()
    socket.value = null
    isConnected.value = false
    isSlidesReady.value = false
    currentSlide.value = 1
    totalSlides.value = 0
    lastError.value = null
  }

  const logout = () => {
    disconnect()
    clearSession()
  }

  return {
    isConnected,
    currentSlide,
    totalSlides,
    isSlidesReady,
    lastError,
    connect,
    send,
    disconnect,
    logout,
  }
})