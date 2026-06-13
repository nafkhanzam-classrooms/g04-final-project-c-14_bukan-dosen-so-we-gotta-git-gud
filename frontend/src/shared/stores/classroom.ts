import { defineStore } from 'pinia'
import { ref, nextTick } from 'vue'

const STORAGE_KEY = 'classroom_session_id'

export interface LeaderboardEntry {
  name: string;
  score: number;
  is_streak: boolean;
}

export const useClassroomStore = defineStore('classroom', () => {
  const socket = ref<WebSocket | null>(null)
  const isConnected = ref(false)
  const sessionId = ref<string | null>(null)
  const lastError = ref<string | null>(null)
  const students = ref<Array<{ name: string; score: number }>>([])
  const currentUser = ref<{ name: string; score: number } | null>(null)
  const roomEnded = ref(false)
  const finalLeaderboard = ref<LeaderboardEntry[]>([])

  const currentSlide = ref(1)
  const totalSlides = ref(0)
  const isSlidesReady = ref(false)

  const syncFailed = ref(false)
  let syncTimeout: ReturnType<typeof setTimeout> | null = null
  let currentConnectionId = 0

  let activeRoomCode: string | null = null
  let activeRole: 'host' | 'student' | null = null
  let activeStudentName: string | null = null

  const loadSavedSession = (): string | null => localStorage.getItem(STORAGE_KEY)

  const saveSession = (id: string) => {
    sessionId.value = id
    localStorage.setItem(STORAGE_KEY, id)
  }
  
  const clearSession = () => {
    sessionId.value = null
    localStorage.removeItem(STORAGE_KEY)
  }

  const activeQuiz = ref<{
    questionId: string | null
    options: string[]
    isActive: boolean
    totalAnswered: number
    correctAnswer: string | null
    stats: Record<string, number> | null
  }>({
    questionId: null,
    options: [],
    isActive: false,
    totalAnswered: 0,
    correctAnswer: null,
    stats: null,
  })

  const send = (event: string, data: any) => {
    if (socket.value?.readyState === WebSocket.OPEN) {
      socket.value.send(JSON.stringify({ event, data }))
      return true
    }
    return false
  }

  // Quiz actions
  const startQuiz = (classCode: string, questionId: string, options: string[]) => {
    send('quiz:start', { class_code: classCode, question_id: questionId, options })
  }
  const answerQuiz = (classCode: string, questionId: string, answer: string) => {
    send('quiz:answer', { class_code: classCode, question_id: questionId, answer })
  }
  const stopQuiz = (classCode: string, questionId: string) => {
    send('quiz:stop', { class_code: classCode, question_id: questionId })
  }
  const closeQuiz = (classCode: string, questionId: string, correctAnswer: string) => {
    send('quiz:close', { class_code: classCode, question_id: questionId, correct_answer: correctAnswer })
  }
  const resetQuiz = () => {
    activeQuiz.value = {
      questionId: null,
      options: [],
      isActive: false,
      totalAnswered: 0,
      correctAnswer: null,
      stats: null,
    }
  }
  const endClassroom = (classCode: string) => {
    send('classroom:end', { class_code: classCode })
  }

  const connect = (roomCode: string, role: 'host' | 'student', username: string = 'Anonymous') => {
    disconnect()

    activeRoomCode = roomCode
    activeRole = role
    activeStudentName = username

    lastError.value = null
    roomEnded.value = false
    finalLeaderboard.value = []
    resetQuiz()

    const wsUrl = import.meta.env.VITE_WS_URL
    const newSocket = new WebSocket(wsUrl)
    const connectionId = ++currentConnectionId
    socket.value = newSocket

    let isReconnectAttempt = false

    newSocket.onopen = () => {
      if (connectionId !== currentConnectionId || socket.value !== newSocket) return
      isConnected.value = true
      const savedId = loadSavedSession()
      if (savedId) {
        isReconnectAttempt = true
        newSocket.send(JSON.stringify({
          event: 'connection:init',
          data: { session_id: savedId }
        }))
      } else {
        isReconnectAttempt = false
        newSocket.send(JSON.stringify({
          event: 'connection:init',
          data: {}
        }))
      }
    }

    newSocket.onmessage = (event) => {
      if (connectionId !== currentConnectionId) return
      const payload = JSON.parse(event.data)

      if (payload.event === 'connection:assigned') {
        saveSession(payload.data.session_id)

        if (activeRole === 'host') {
          send('classroom:create', { class_code: activeRoomCode })
        } else if (activeRole === 'student') {
          send('classroom:join', { class_code: activeRoomCode, student_name: activeStudentName })
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

    newSocket.onclose = () => {
      if (connectionId === currentConnectionId) {
        isConnected.value = false
        socket.value = null
      }
    }

    newSocket.onerror = (err) => {
      console.error('WebSocket error', err)
      if (connectionId === currentConnectionId) {
        lastError.value = 'Connection error. Please refresh.'
      }
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
        if (syncTimeout) clearTimeout(syncTimeout)
        syncFailed.value = false
        totalSlides.value = data.total_slides || 0
        currentSlide.value = data.current_slide || 1
        if (totalSlides.value > 0) isSlidesReady.value = true

        if (Array.isArray(data.active_students)) {
          students.value = data.active_students.map((name: string) => ({ name, score: 0 }))
        } else {
          students.value = []
        }
        break

      case 'classroom:created':
        lastError.value = null
        send('classroom:sync', { class_code: activeRoomCode })
        break

      case 'classroom:joined':
        lastError.value = null
        if (data.student_name) {
          currentUser.value = { name: data.student_name, score: 0 }
        } else {
          console.warn('classroom:joined missing student_name', data)
        }
        send('classroom:sync', { class_code: activeRoomCode })
        break

      case 'classroom:error':
        console.error('Classroom error:', data.message)
        lastError.value = data.message
        // Persist the error so it's not lost
        if (data.message?.toLowerCase().includes('not found') || data.message?.toLowerCase().includes('does not exist')) {
          console.warn('Classroom not found, disconnecting')
          disconnect()
          clearSession()
        }
        break

      case 'quiz:started':
        activeQuiz.value = {
          questionId: data.question_id,
          options: data.options,
          isActive: true,
          totalAnswered: 0,
          correctAnswer: null,
          stats: null,
        }
        break

      case 'quiz:answer_received':
        if (activeQuiz.value && activeQuiz.value.questionId) {
          activeQuiz.value.totalAnswered = data.total_answered
        }
        break

      case 'quiz:stopped':
        if (activeQuiz.value) {
          activeQuiz.value.isActive = false
        }
        break

      case 'quiz:closed':
        if (activeQuiz.value && activeQuiz.value.questionId === data.question_id) {
          activeQuiz.value.isActive = false
          activeQuiz.value.correctAnswer = data.correct_answer
          activeQuiz.value.stats = data.stats
        }
        break

      case 'game:score_update':
        if (currentUser.value) {
          currentUser.value.score = data.total_score
        }
        break

      case 'classroom:ended':
        finalLeaderboard.value = data.top_students || []
        roomEnded.value = true
        clearSession() // so that a reload doesn't try to rejoin an ended room
        break
    }
  }

  const disconnect = () => {
    if (socket.value) {
      socket.value.onopen = null
      socket.value.onmessage = null
      socket.value.onclose = null
      socket.value.onerror = null
      if (socket.value.readyState === WebSocket.OPEN) {
        socket.value.close()
      }
      socket.value = null
    }
    isConnected.value = false
    isSlidesReady.value = false
    currentSlide.value = 1
    totalSlides.value = 0
    lastError.value = null
    resetQuiz()
    activeRoomCode = null
    activeRole = null
    activeStudentName = null
    currentConnectionId++
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
    activeQuiz,
    startQuiz,
    answerQuiz,
    stopQuiz,
    closeQuiz,
    resetQuiz,
    students,
    currentUser,
    roomEnded,
    finalLeaderboard,
    endClassroom
  }
})