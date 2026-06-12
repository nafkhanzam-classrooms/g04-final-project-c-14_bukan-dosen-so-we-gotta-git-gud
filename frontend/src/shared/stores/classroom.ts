import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useClassroomStore = defineStore('classroom', () => {
  const socket = ref<WebSocket | null>(null)
  const isConnected = ref(false)
  const sessionId = ref<string | null>(null)

  // Slide state
  const currentSlide = ref(1)
  const totalSlides = ref(0)
  const isSlidesReady = ref(false)

  const connect = (roomCode: string, role: 'host' | 'student', username: string = 'Anonymous') => {
    if (socket.value?.readyState === WebSocket.OPEN) return

    const wsUrl = import.meta.env.VITE_WS_URL
    socket.value = new WebSocket(wsUrl)

    socket.value.onopen = () => {
      isConnected.value = true
      socket.value?.send(JSON.stringify({}))
    }

    socket.value.onmessage = (event) => {
      const payload = JSON.parse(event.data)
      if (payload.event === 'connection:assigned') {
        sessionId.value = payload.data.session_id
        if (role === 'host') {
          send('classroom:create', { class_code: roomCode })
        } else {
          send('classroom:join', { class_code: roomCode, student_name: username })
        }
        return
      }
      handleIncomingEvent(payload.event, payload.data)
    }

    socket.value.onclose = () => {
      isConnected.value = false
      sessionId.value = null
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
        isSlidesReady.value = true
        currentSlide.value = 1
        break
      case 'slides:changed':
        currentSlide.value = data.slide_number
        break
      case 'classroom:created':
      case 'classroom:joined':
        break
      case 'classroom:error':
        console.error('Classroom error:', data.message)
        break
    }
  }

  const disconnect = () => {
    socket.value?.close()
    socket.value = null
    sessionId.value = null
    isSlidesReady.value = false
    currentSlide.value = 1
    totalSlides.value = 0
  }

  return {
    isConnected,
    currentSlide,
    totalSlides,
    isSlidesReady,
    connect,
    send,
    disconnect,
  }
})
