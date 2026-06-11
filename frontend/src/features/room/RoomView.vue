<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import LeaderboardPanel from './components/LeaderboardPanel.vue'
import QuizPanel from './components/QuizPanel.vue'

const route = useRoute()
const router = useRouter()
const roomId = route.params.roomId as string
const isHost = route.query.role === 'host'

// Room 4 Phase State Machine
type SessionPhase = 'upload' | 'present' | 'quiz' | 'ended'
const phase = ref<SessionPhase>(isHost ? 'upload' : 'present')

// Modal State
const showEndSessionModal = ref(false)

// Upload State
const fileToUpload = ref<File | null>(null)
const handleFileUpload = (e: Event) => {
  const target = e.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    const file = target.files[0]
    if (file) {
      fileToUpload.value = file

      // TODO: Call worker to process file and prepare presentation data
    }
  }
}
const startPresentation = () => {
  phase.value = 'present'
}

// Quiz State
const showQuizMenu = ref(false)
const quizType = ref<'mcq' | 'text' | null>(null)
const correctAnswer = ref<string>('')

const startQuiz = (type: 'mcq' | 'text') => {
  quizType.value = type
  phase.value = 'quiz'
  showQuizMenu.value = false
}

const endQuiz = () => {
  phase.value = 'present'
  quizType.value = null
  correctAnswer.value = ''
}

// Session Controls
const promptEndSession = () => {
  showEndSessionModal.value = true
}

const confirmEndSession = () => {
  phase.value = 'ended'
  showEndSessionModal.value = false
}

const exitClass = () => {
  
  // TODO: Add any necessary cleanup or API calls to leave the room gracefully

  router.push('/')
}

// TODO: Replace with actual student data from API and real-time updates via WebSocket
const students = ref([
  { name: 'Yasfin', score: 250 },
  { name: 'Nafkhan', score: 210 },
  { name: 'Alice', score: 180 },
])

const sortedStudents = computed(() => {
  return [...students.value].sort((a, b) => b.score - a.score)
})
</script>

<template>
  <div class="flex h-screen bg-zinc-950 text-neutral-200 font-sans relative">
    
    <main class="flex-1 flex flex-col min-w-0 relative">
      
      <header class="h-16 border-b border-zinc-800 bg-zinc-900/80 flex justify-between items-center px-6 sticky top-0 z-10">
        <div class="flex items-center gap-3">
          <span class="text-zinc-400 font-medium">Room:</span>
          <span class="text-xl font-mono font-bold text-neutral-100 bg-zinc-800 px-3 py-1 rounded-md">
            {{ roomId }}
          </span>
        </div>
        <div class="flex items-center gap-4">
          <div 
            class="px-3 py-1 rounded text-xs font-bold uppercase tracking-wide"
            :class="isHost ? 'bg-neutral-200 text-zinc-900' : 'bg-zinc-800 text-zinc-300'"
          >
            {{ isHost ? 'Host' : 'Student' }}
          </div>
          
          <button 
            v-if="isHost && phase !== 'ended'" 
            @click="promptEndSession"
            class="px-4 py-1.5 bg-red-900/50 hover:bg-red-900 text-red-200 border border-red-800 rounded-md text-sm font-semibold transition"
          >
            End Session
          </button>

          <button 
            v-if="!isHost && phase !== 'ended'" 
            @click="exitClass"
            class="px-4 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 border border-zinc-700 rounded-md text-sm font-semibold transition"
          >
            Exit Class
          </button>
        </div>
      </header>

      <div v-if="phase === 'upload' && isHost" class="flex-1 flex items-center justify-center p-10">
        <div class="w-full max-w-2xl bg-zinc-900 border-2 border-dashed border-zinc-700 rounded-2xl p-12 text-center">
          <h2 class="text-3xl font-bold text-neutral-100 mb-4">Upload Presentation</h2>
          <p class="text-zinc-400 mb-8">Select a .pptx or .pdf file to process and start the class.</p>
          
          <input 
            type="file" 
            accept=".pptx,.pdf" 
            class="hidden" 
            id="file-upload"
            @change="handleFileUpload"
          />
          <label 
            for="file-upload" 
            class="cursor-pointer inline-block bg-zinc-800 border border-zinc-700 hover:bg-zinc-700 text-neutral-200 font-medium py-3 px-6 rounded-lg transition mb-6"
          >
            {{ fileToUpload ? fileToUpload.name : 'Choose File' }}
          </label>
          
          <div v-if="fileToUpload">
            <button 
              @click="startPresentation"
              class="w-full bg-neutral-100 text-zinc-950 font-bold py-4 rounded-xl hover:bg-neutral-300 transition shadow-lg"
            >
              Start Class
            </button>
          </div>
        </div>
      </div>

      <div v-else-if="phase === 'upload' && !isHost" class="flex-1 flex flex-col items-center justify-center">
        <div class="animate-pulse w-16 h-16 bg-zinc-800 rounded-full mb-6"></div>
        <h2 class="text-2xl font-bold text-neutral-100">Waiting for Teacher...</h2>
        <p class="text-zinc-500 mt-2">The presentation material is being prepared.</p>
      </div>

      <LeaderboardPanel v-else-if="phase === 'ended'" :students="students" />

      <template v-else>
        <div class="flex-1 flex items-center justify-center p-6 lg:p-10 overflow-hidden relative">
          <div class="w-full h-full max-w-6xl bg-black border border-zinc-800 rounded-xl shadow-2xl flex items-center justify-center aspect-video relative">
            <p class="text-zinc-600 font-medium text-lg">Slide Container</p>
            
            <QuizPanel 
              v-if="phase === 'quiz'" 
              :is-host="isHost" 
              :quiz-type="quizType" 
              @close-quiz="endQuiz" 
            />
          </div>
        </div>

        <footer v-if="isHost" class="h-20 border-t border-zinc-800 bg-zinc-900/80 flex items-center justify-between px-6 z-20">
          <div class="flex gap-2">
            <button class="w-10 h-10 flex items-center justify-center bg-zinc-800 hover:bg-zinc-700 rounded-lg text-neutral-300 transition">
              &larr;
            </button>
            <button class="w-10 h-10 flex items-center justify-center bg-zinc-800 hover:bg-zinc-700 rounded-lg text-neutral-300 transition">
              &rarr;
            </button>
          </div>
          
          <div class="relative">
            <div v-if="showQuizMenu" class="absolute bottom-full left-1/2 -translate-x-1/2 mb-4 w-48 bg-zinc-800 border border-zinc-700 rounded-xl shadow-2xl overflow-hidden p-1">
              <button @click="startQuiz('mcq')" class="w-full text-left px-4 py-3 hover:bg-zinc-700 rounded-lg text-sm font-medium transition flex items-center gap-2">
                <span class="bg-blue-900/50 text-blue-400 w-6 h-6 flex items-center justify-center rounded">A</span> Multiple Choice
              </button>
              <button @click="startQuiz('text')" class="w-full text-left px-4 py-3 hover:bg-zinc-700 rounded-lg text-sm font-medium transition flex items-center gap-2">
                <span class="bg-green-900/50 text-green-400 w-6 h-6 flex items-center justify-center rounded">T</span> Short Answer
              </button>
            </div>
            
            <button 
              @click="showQuizMenu = !showQuizMenu"
              class="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-bold transition shadow-lg flex items-center gap-2"
              :class="{'ring-2 ring-indigo-400 ring-offset-2 ring-offset-zinc-900': showQuizMenu}"
            >
              Pop Quiz
            </button>
          </div>
          
          <div class="text-sm font-medium text-zinc-500">
            Slide 1 / 10
          </div>
        </footer>
      </template>
    </main>

    <aside v-if="phase === 'present' || phase === 'quiz'" class="w-80 border-l border-zinc-800 bg-zinc-900/30 flex flex-col hidden md:flex z-10">
      <div class="h-16 border-b border-zinc-800 flex items-center px-6">
        <h3 class="font-semibold text-neutral-100 flex items-center gap-2">
          <span class="w-2 h-2 rounded-full bg-green-500"></span> Live Scores
        </h3>
      </div>
      <div class="flex-1 p-4 overflow-y-auto">
        <div class="space-y-2">
          <div 
            v-for="student in sortedStudents" 
            :key="student.name"
            class="bg-zinc-800/40 border border-zinc-800/80 p-3 rounded-lg flex justify-between items-center"
          >
            <span class="font-medium text-neutral-300">{{ student.name }}</span>
            <span class="bg-zinc-900 text-zinc-400 px-2 py-1 rounded text-xs font-bold font-mono">
              {{ student.score }}
            </span>
          </div>
        </div>
      </div>
    </aside>

    <div 
      v-if="showEndSessionModal" 
      class="absolute inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
    >
      <div class="bg-zinc-900 border border-zinc-800 p-8 rounded-2xl shadow-2xl max-w-sm w-full text-center">
        <h3 class="text-2xl font-bold text-neutral-100 mb-2">End Session?</h3>
        <p class="text-zinc-400 mb-8">This will close the active room and display the final leaderboard for all participants.</p>
        
        <div class="flex gap-4">
          <button 
            @click="showEndSessionModal = false" 
            class="flex-1 px-4 py-3 bg-zinc-800 hover:bg-zinc-700 text-neutral-200 rounded-xl font-medium transition"
          >
            Cancel
          </button>
          <button 
            @click="confirmEndSession" 
            class="flex-1 px-4 py-3 bg-red-600 hover:bg-red-500 text-white rounded-xl font-bold transition shadow-lg shadow-red-900/20"
          >
            End Session
          </button>
        </div>
      </div>
    </div>

  </div>
</template>