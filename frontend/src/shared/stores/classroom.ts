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

  const updateStudentScore = (studentName: string, newScore: number) => {
    const idx = students.value.findIndex(s => s.name === studentName)
    if (idx !== -1) {
      const student = students.value[idx]
      if (student) student.score = newScore
    } else {
      students.value.push({ name: studentName, score: newScore })
    }
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
          syncTimeout = setTimeout(() => {
            syncFailed.value = true
            lastError.value = 'Connection lost – please rejoin the room.'
            disconnect()
            clearSession()
          }, 5000)
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
        if (syncTimeout) clearTimeout(syncTimeout)
        syncFailed.value = false
        totalSlides.value = data.total_slides
        currentSlide.value = data.current_slide
        nextTick(() => { isSlidesReady.value = true })
        
        const newStudents = Object.values(data.active_students).map((s: any) => ({
          name: s.name,
          score: 0
        }))
        students.value = newStudents
        break
      case 'classroom:created':
      case 'classroom:joined':
        lastError.value = null
        if (data.student) {
          currentUser.value = { name: data.student.name, score: 0 }
        } else {
          console.warn('classroom:joined missing student data', data)
        }
        send('classroom:sync', {})
        break
      case 'classroom:error':
        console.error('Classroom error:', data.message)
        lastError.value = data.message
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
        disconnect()
        clearSession()
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