<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useClassroomStore } from '@/shared/stores/classroom'
import { storeToRefs } from 'pinia'
import QuizPanel from './components/QuizPanel.vue'

const props = defineProps<{
  roomId: string
  role: 'host' | 'student'
  studentName: string | null
}>()
const emit = defineEmits(['exit'])

const API_BASE_URL = import.meta.env.VITE_API_URL || ''
const store = useClassroomStore()
const { currentSlide, totalSlides, isSlidesReady, lastError, currentUser, roomEnded, finalLeaderboard } = storeToRefs(store)

type SessionPhase = 'upload' | 'present' | 'quiz' | 'ended'

function initialPhase(): SessionPhase {
  if (roomEnded.value) return 'ended'
  if (totalSlides.value > 0 && isSlidesReady.value) return 'present'
  return 'upload'
}
const phase = ref<SessionPhase>(initialPhase())
watch([totalSlides, isSlidesReady], ([slides, ready]) => {
  if (props.role === 'host' && ready && slides > 0 && phase.value !== 'quiz') {
    phase.value = 'present'
  }
})

const uploadStatus = ref<'idle' | 'uploading' | 'converting' | 'success' | 'error'>('idle')
const statusMessage = ref('')
let conversionTimeout: ReturnType<typeof setTimeout> | null = null
const fileToUpload = ref<File | null>(null)

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

onMounted(() => {
  const name = props.role === 'host' ? 'Teacher' : (props.studentName || 'Student')
  store.connect(props.roomId, props.role, name)
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
    const response = await fetch(`${API_BASE_URL}/upload/${props.roomId}/${ext}`, {
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
    store.send('slides:change', { class_code: props.roomId, slide_number: currentSlide.value + 1 })
  }
}

const prevSlide = () => {
  if (currentSlide.value > 1) {
    store.send('slides:change', { class_code: props.roomId, slide_number: currentSlide.value - 1 })
  }
}

const showQuizMenu = ref(false)
const startQuiz = () => { phase.value = 'quiz'; showQuizMenu.value = false }
const endQuiz = () => { if (!roomEnded.value) phase.value = 'present' }

const showEndSessionModal = ref(false)
const promptEndSession = () => { showEndSessionModal.value = true }
const confirmEndSession = () => {
  showEndSessionModal.value = false
  store.endClassroom(props.roomId)
}
const exitClass = () => {
  store.logout()
  emit('exit')
}
</script>

<template>
  <div class="h-screen bg-zinc-950 text-neutral-200 font-sans flex flex-col overflow-hidden">
    <header class="h-16 border-b border-zinc-800 bg-zinc-900/80 flex justify-between items-center px-4 sm:px-6 shrink-0">
      <div class="flex items-center gap-2 sm:gap-3">
        <span class="text-zinc-400 font-medium text-sm sm:text-base">Room:</span>
        <span class="text-base sm:text-xl font-mono font-bold text-neutral-100 bg-zinc-800 px-2 sm:px-3 py-1 rounded-md">{{ roomId }}</span>
      </div>
      <div class="flex items-center gap-2 sm:gap-4">
        <div class="px-2 sm:px-3 py-1 rounded text-xs font-bold uppercase tracking-wide" :class="role === 'host' ? 'bg-neutral-200 text-zinc-900' : 'bg-zinc-800 text-zinc-300'">
          {{ role === 'host' ? 'Host' : 'Student' }}
        </div>
        <button v-if="role === 'host' && !roomEnded" @click="promptEndSession" class="px-3 sm:px-4 py-1.5 bg-red-900/50 hover:bg-red-900 text-red-200 border border-red-800 rounded-md text-xs sm:text-sm font-semibold transition">
          End
        </button>
        <button v-if="role === 'student' && !roomEnded" @click="exitClass" class="px-3 sm:px-4 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 border border-zinc-700 rounded-md text-xs sm:text-sm font-semibold transition">
          Exit
        </button>
      </div>
    </header>

    <div class="flex-1 overflow-hidden">
      <div v-if="roomEnded" class="h-full flex flex-col items-center justify-center p-4 overflow-y-auto">
        <div class="w-full max-w-lg bg-zinc-900 border border-zinc-800 rounded-2xl shadow-2xl overflow-hidden">
          <div class="p-6 text-center border-b border-zinc-800">
            <h1 class="text-2xl sm:text-3xl font-bold text-neutral-100">Session Ended</h1>
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
        <button @click="emit('exit')" class="mt-8 px-6 py-2 bg-neutral-100 text-zinc-950 rounded-lg font-bold hover:bg-neutral-300 transition">
          ← Go Home
        </button>
      </div>

      <div v-else-if="phase === 'upload' && role === 'host'" class="h-full flex items-center justify-center p-4 overflow-y-auto">
        <div class="w-full max-w-2xl bg-zinc-900 border-2 border-dashed border-zinc-700 rounded-2xl p-6 sm:p-12 text-center">
          <h2 class="text-2xl sm:text-3xl font-bold text-neutral-100 mb-4">Upload Presentation</h2>
          <p class="text-zinc-400 mb-8 text-sm sm:text-base">Select a .pptx or .pdf file. Conversion may take a few seconds.</p>
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

      <div v-else-if="phase === 'upload' && role === 'student'" class="h-full flex flex-col items-center justify-center p-4">
        <div class="animate-pulse w-16 h-16 bg-zinc-800 rounded-full mb-6"></div>
        <h2 class="text-2xl font-bold text-neutral-100">Waiting for Teacher...</h2>
        <p class="text-zinc-500 mt-2">The presentation material is being prepared.</p>
      </div>

      <template v-else>
        <div v-if="role === 'host'" class="h-full flex flex-col">
          <div class="flex-1 flex items-center justify-center p-2 sm:p-4 overflow-hidden">
            <div class="w-full h-full flex items-center justify-center">
              <img v-if="totalSlides > 0" :src="`${API_BASE_URL}/slides/${roomId}/${slideFilename}`" class="max-h-full max-w-full object-contain" alt="Slide" />
              <p v-else class="text-zinc-600">Loading slides...</p>
            </div>
          </div>
          <div class="h-20 border-t border-zinc-800 bg-zinc-900/80 flex items-center justify-between px-4 sm:px-6 shrink-0">
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
              <button @click="showQuizMenu = !showQuizMenu" class="px-4 sm:px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-bold transition shadow-lg text-sm sm:text-base">
                Pop Quiz
              </button>
            </div>
            <div class="text-sm text-zinc-500">Slide {{ currentSlide }} / {{ totalSlides }}</div>
          </div>
          <QuizPanel v-if="phase === 'quiz'" :is-host="true" :room-id="roomId" @close-quiz="endQuiz" class="shrink-0" />
        </div>

        <div v-else class="h-full grid grid-cols-1 lg:grid-cols-[70%_30%] grid-rows-[60%_40%] lg:grid-rows-1">
          <div class="flex items-center justify-center p-2 sm:p-4 order-1 overflow-hidden">
            <div class="w-full h-full flex items-center justify-center">
              <img v-if="totalSlides > 0" :src="`${API_BASE_URL}/slides/${roomId}/${slideFilename}`" class="max-h-full max-w-full object-contain" alt="Slide" />
              <p v-else class="text-zinc-600">Loading slides...</p>
            </div>
          </div>
          <aside class="border-t lg:border-t-0 lg:border-l border-zinc-800 bg-zinc-900/30 p-4 flex flex-col gap-4 overflow-y-auto order-2">
            <div class="bg-zinc-800/40 border border-zinc-800/80 rounded-lg p-4">
              <div class="text-sm text-zinc-400">You</div>
              <div class="text-xl font-bold">{{ currentUser?.name || 'Student' }}</div>
              <div class="text-2xl font-mono mt-2 text-indigo-400">{{ currentUser?.score || 0 }} pts</div>
            </div>
            <div class="flex-1">
              <QuizPanel :is-host="false" :room-id="roomId" @close-quiz="endQuiz" />
            </div>
          </aside>
        </div>
      </template>
    </div>

    <div v-if="showEndSessionModal" class="fixed inset-0 z-[70] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div class="bg-zinc-900 border border-zinc-800 p-6 sm:p-8 rounded-2xl shadow-2xl max-w-sm w-full text-center">
        <h3 class="text-xl sm:text-2xl font-bold text-neutral-100 mb-2">End Session?</h3>
        <p class="text-zinc-400 mb-6 sm:mb-8 text-sm sm:text-base">This will close the active room and display the final leaderboard for all participants.</p>
        <div class="flex gap-4">
          <button @click="showEndSessionModal = false" class="flex-1 px-4 py-3 bg-zinc-800 hover:bg-zinc-700 text-neutral-200 rounded-xl font-medium">Cancel</button>
          <button @click="confirmEndSession" class="flex-1 px-4 py-3 bg-red-600 hover:bg-red-500 text-white rounded-xl font-bold">End Session</button>
        </div>
      </div>
    </div>
  </div>
</template>