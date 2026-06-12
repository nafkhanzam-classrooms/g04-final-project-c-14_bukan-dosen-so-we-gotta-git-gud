<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useClassroomStore } from '@/shared/stores/classroom'
import { storeToRefs } from 'pinia'
import QuizPanel from './components/QuizPanel.vue'

const API_BASE_URL = import.meta.env.VITE_API_URL || ''
const route = useRoute()
const router = useRouter()
const roomId = route.params.roomId as string
const isHost = route.query.role === 'host'
const store = useClassroomStore()
const { currentSlide, totalSlides, isSlidesReady, lastError, currentUser, roomEnded, finalLeaderboard } = storeToRefs(store)

type SessionPhase = 'upload' | 'present' | 'quiz' | 'ended'
const phase = ref<SessionPhase>(isHost ? 'upload' : 'present')

const uploadStatus = ref<'idle' | 'uploading' | 'converting' | 'success' | 'error'>('idle')
const statusMessage = ref('')
let conversionTimeout: ReturnType<typeof setTimeout> | null = null
const fileToUpload = ref<File | null>(null)

watch(lastError, (err) => {
  if (err && !isHost) {
    router.push({ path: '/join', query: { error: err } })
  } else if (err && isHost) {
    router.push({ path: '/host', query: { error: err } })
  }
})

watch([isSlidesReady, totalSlides], ([ready, slides]) => {
  if (ready && slides > 0) {
    if (conversionTimeout) clearTimeout(conversionTimeout)
    conversionTimeout = null
    uploadStatus.value = 'success'
    statusMessage.value = ''
    if (phase.value === 'upload') phase.value = 'present'
  } else if (ready && slides === 0) {
    uploadStatus.value = 'error'
    statusMessage.value = 'Conversion failed – no slides generated. Please try a different PDF file.'
    phase.value = 'upload'
    fileToUpload.value = null
  }
})

// Trigger perpindahan fase ke ended saat broadcast classroom:ended ditangkap
watch(roomEnded, (ended) => {
  if (ended) {
    phase.value = 'ended'
  }
})

onMounted(() => {
  const studentName = route.query.studentName as string || 'Student'
  store.connect(roomId, isHost ? 'host' : 'student', isHost ? 'Teacher' : studentName)
})

onUnmounted(() => {
  if (conversionTimeout) clearTimeout(conversionTimeout)
  store.disconnect()
})

const handleFileUpload = async (e: Event) => {
  const target = e.target as HTMLInputElement
  if (!target.files || target.files.length === 0) return
  const file = target.files[0]
  if (!file) return

  fileToUpload.value = file
  uploadStatus.value = 'uploading'
  statusMessage.value = 'Uploading file...'
  if (conversionTimeout) clearTimeout(conversionTimeout)

  const ext = file.name.split('.').pop()?.toLowerCase()
  if (ext !== 'pdf' && ext !== 'pptx') {
    uploadStatus.value = 'error'
    statusMessage.value = 'Only PDF or PPTX files are supported.'
    fileToUpload.value = null
    return
  }

  try {
    const response = await fetch(`${API_BASE_URL}/upload/${roomId}/${ext}`, {
      method: 'POST',
      body: file,
      headers: { 'Content-Type': 'application/octet-stream' }
    })
    if (!response.ok) throw new Error(`Upload failed: ${response.status}`)

    uploadStatus.value = 'converting'
    statusMessage.value = 'Converting slides...'
    conversionTimeout = setTimeout(() => {
      if (!isSlidesReady.value || totalSlides.value === 0) {
        uploadStatus.value = 'error'
        statusMessage.value = 'Conversion timed out. Please try again (PDF works best).'
        phase.value = 'upload'
        fileToUpload.value = null
      }
      conversionTimeout = null
    }, 120000)
  } catch (err) {
    console.error(err)
    uploadStatus.value = 'error'
    statusMessage.value = 'Upload failed. Please check your connection and try again.'
    fileToUpload.value = null
  }
}

const resetUpload = () => {
  if (conversionTimeout) clearTimeout(conversionTimeout)
  uploadStatus.value = 'idle'
  statusMessage.value = ''
  fileToUpload.value = null
  phase.value = 'upload'
}

const slideFilename = computed(() => {
  const width = String(totalSlides.value).length
  return `slide-${String(currentSlide.value).padStart(width, '0')}.webp`
})

const nextSlide = () => {
  if (currentSlide.value < totalSlides.value) {
    store.send('slides:change', { class_code: roomId, slide_number: currentSlide.value + 1 })
  }
}

const prevSlide = () => {
  if (currentSlide.value > 1) {
    store.send('slides:change', { class_code: roomId, slide_number: currentSlide.value - 1 })
  }
}

// Quiz state
const showQuizMenu = ref(false)

const startQuiz = () => {
  console.log('Starting quiz...')
  phase.value = 'quiz'
  console.log('Quiz is true...')
  showQuizMenu.value = false
  console.log('Menu quiz...')
}

const endQuiz = () => {
  console.log('Ending quiz...')
  phase.value = 'present'
}

// Session Controls
const showEndSessionModal = ref(false)
const promptEndSession = () => { showEndSessionModal.value = true }
const confirmEndSession = () => {
  showEndSessionModal.value = false
  store.endClassroom(roomId)
}
const exitClass = () => {
  store.logout()
  router.push('/')
}
</script>

<template>
  <div class="h-screen bg-zinc-950 text-neutral-200 font-sans">
    <header class="h-16 border-b border-zinc-800 bg-zinc-900/80 flex justify-between items-center px-6 sticky top-0 z-10">
      <div class="flex items-center gap-3">
        <span class="text-zinc-400 font-medium">Room:</span>
        <span class="text-xl font-mono font-bold text-neutral-100 bg-zinc-800 px-3 py-1 rounded-md">{{ roomId }}</span>
      </div>
      <div class="flex items-center gap-4">
        <div class="px-3 py-1 rounded text-xs font-bold uppercase tracking-wide" :class="isHost ? 'bg-neutral-200 text-zinc-900' : 'bg-zinc-800 text-zinc-300'">
          {{ isHost ? 'Host' : 'Student' }}
        </div>
        <button v-if="isHost && phase !== 'ended'" @click="promptEndSession" class="px-4 py-1.5 bg-red-900/50 hover:bg-red-900 text-red-200 border border-red-800 rounded-md text-sm font-semibold transition">
          End Session
        </button>
        <button v-if="!isHost && phase !== 'ended'" @click="exitClass" class="px-4 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 border border-zinc-700 rounded-md text-sm font-semibold transition">
          Exit Class
        </button>
      </div>
    </header>

    <div class="h-[calc(100vh-4rem)] overflow-hidden">
      <div v-if="phase === 'upload' && isHost" class="flex items-center justify-center h-full">
        <div class="w-full max-w-2xl bg-zinc-900 border-2 border-dashed border-zinc-700 rounded-2xl p-12 text-center">
          <h2 class="text-3xl font-bold text-neutral-100 mb-4">Upload Presentation</h2>
          <p class="text-zinc-400 mb-8">Select a .pptx or .pdf file. Conversion may take a few seconds.</p>
          <div v-if="statusMessage" class="mb-4 p-3 rounded-lg text-sm" :class="{
            'bg-blue-900/50 text-blue-200': uploadStatus === 'uploading' || uploadStatus === 'converting',
            'bg-red-900/50 text-red-200': uploadStatus === 'error',
            'bg-green-900/50 text-green-200': uploadStatus === 'success'
          }">{{ statusMessage }}</div>
          <input type="file" accept=".pptx,.pdf" class="hidden" id="file-upload" @change="handleFileUpload" :disabled="uploadStatus === 'uploading' || uploadStatus === 'converting'" />
          <label for="file-upload" class="cursor-pointer inline-block bg-zinc-800 border border-zinc-700 hover:bg-zinc-700 text-neutral-200 font-medium py-3 px-6 rounded-lg transition mb-6" :class="{'opacity-50 cursor-not-allowed': uploadStatus === 'uploading' || uploadStatus === 'converting'}">
            {{ fileToUpload ? fileToUpload.name : 'Choose File' }}
          </label>
          <div v-if="uploadStatus === 'error'">
            <button @click="resetUpload" class="text-sm text-zinc-400 underline mt-2">Try another file</button>
          </div>
        </div>
      </div>

      <div v-else-if="phase === 'upload' && !isHost" class="flex flex-col items-center justify-center h-full">
        <div class="animate-pulse w-16 h-16 bg-zinc-800 rounded-full mb-6"></div>
        <h2 class="text-2xl font-bold text-neutral-100">Waiting for Teacher...</h2>
        <p class="text-zinc-500 mt-2">The presentation material is being prepared.</p>
      </div>

      <div v-else-if="phase === 'ended'" class="flex flex-col items-center justify-center h-full">
        <div class="w-full max-w-lg bg-zinc-900 border border-zinc-800 rounded-2xl shadow-2xl overflow-hidden">
          <div class="p-6 text-center border-b border-zinc-800">
            <h1 class="text-3xl font-bold text-neutral-100">Session Ended</h1>
            <p class="text-zinc-400">Final Leaderboard</p>
          </div>
          <div class="divide-y divide-zinc-800 max-h-[60vh] overflow-y-auto">
            <div v-for="(student, idx) in finalLeaderboard" :key="student.name" class="p-4 flex justify-between items-center">
              <div class="flex items-center gap-3">
                <span class="text-lg font-bold text-zinc-500 w-6">{{ idx+1 }}</span>
                <span class="text-neutral-200">{{ student.name }}</span>
                <span v-if="student.is_streak" class="px-2 py-0.5 rounded text-xs font-bold bg-orange-900/40 text-orange-400 border border-orange-700">
                  🔥 Streak
                </span>
              </div>
              <span class="text-xl font-mono">{{ student.score }} pts</span>
            </div>
            <div v-if="finalLeaderboard.length === 0" class="p-6 text-center text-zinc-500">
              No participation data available.
            </div>
          </div>
        </div>
        <button @click="router.push('/')" class="mt-8 px-6 py-2 bg-neutral-100 text-zinc-950 rounded-lg font-bold hover:bg-neutral-300 transition">
          ← Go Home
        </button>
      </div>

      <template v-else>
        <div v-if="isHost" class="flex flex-col h-full relative">
          <div class="flex-1 flex items-center justify-center p-6">
            <div class="w-full max-w-6xl bg-black border border-zinc-800 rounded-xl shadow-2xl aspect-video flex items-center justify-center">
              <img v-if="totalSlides > 0" :src="`${API_BASE_URL}/slides/${roomId}/${slideFilename}`" class="w-full h-full object-contain" alt="Slide" />
              <p v-else class="text-zinc-600">Loading slides...</p>
            </div>
          </div>
          <div class="h-20 border-t border-zinc-800 bg-zinc-900/80 flex items-center justify-between px-6">
            <div class="flex gap-2">
              <button @click="prevSlide" class="w-10 h-10 flex items-center justify-center bg-zinc-800 hover:bg-zinc-700 rounded-lg">&larr;</button>
              <button @click="nextSlide" class="w-10 h-10 flex items-center justify-center bg-zinc-800 hover:bg-zinc-700 rounded-lg">&rarr;</button>
            </div>
            <div class="relative">
              <div v-if="showQuizMenu" class="absolute bottom-full left-1/2 -translate-x-1/2 mb-4 w-48 bg-zinc-800 border border-zinc-700 rounded-xl shadow-2xl overflow-hidden p-1">
                <button @click="startQuiz" class="w-full text-left px-4 py-3 hover:bg-zinc-700 rounded-lg text-sm font-medium">
                  Multiple Choice Quiz
                </button>
              </div>
              <button @click="showQuizMenu = !showQuizMenu" class="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-bold transition shadow-lg">
                Pop Quiz
              </button>
            </div>
            <div class="text-sm text-zinc-500">Slide {{ currentSlide }} / {{ totalSlides }}</div>
          </div>
          <QuizPanel v-if="phase === 'quiz'" :is-host="true" @close-quiz="endQuiz" />
        </div>

        <div v-else class="grid grid-cols-[2fr_1fr] h-full">
          <div class="flex items-center justify-center p-6">
            <div class="w-full bg-black border border-zinc-800 rounded-xl shadow-2xl aspect-video flex items-center justify-center">
              <img v-if="totalSlides > 0" :src="`${API_BASE_URL}/slides/${roomId}/${slideFilename}`" class="w-full h-full object-contain" alt="Slide" />
              <p v-else class="text-zinc-600">Loading slides...</p>
            </div>
          </div>
          <aside class="border-l border-zinc-800 bg-zinc-900/30 p-4 flex flex-col gap-4 overflow-y-auto">
            <div class="bg-zinc-800/40 border border-zinc-800/80 rounded-lg p-4">
              <div class="text-sm text-zinc-400">You</div>
              <div class="text-xl font-bold">{{ currentUser?.name || 'Student' }}</div>
              <div class="text-2xl font-mono mt-2 text-indigo-400">{{ currentUser?.score || 0 }} pts</div>
            </div>
            <div class="flex-1">
              <QuizPanel :is-host="false" @close-quiz="endQuiz" />
            </div>
          </aside>
        </div>
      </template>
    </div>

    <div v-if="showEndSessionModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div class="bg-zinc-900 border border-zinc-800 p-8 rounded-2xl shadow-2xl max-w-sm w-full text-center">
        <h3 class="text-2xl font-bold text-neutral-100 mb-2">End Session?</h3>
        <p class="text-zinc-400 mb-8">This will close the active room and display the final leaderboard for all participants.</p>
        <div class="flex gap-4">
          <button @click="showEndSessionModal = false" class="flex-1 px-4 py-3 bg-zinc-800 hover:bg-zinc-700 text-neutral-200 rounded-xl font-medium">Cancel</button>
          <button @click="confirmEndSession" class="flex-1 px-4 py-3 bg-red-600 hover:bg-red-500 text-white rounded-xl font-bold">End Session</button>
        </div>
      </div>
    </div>
  </div>
</template>