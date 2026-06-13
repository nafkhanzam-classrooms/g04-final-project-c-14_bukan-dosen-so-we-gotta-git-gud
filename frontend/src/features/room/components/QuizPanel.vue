<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useClassroomStore } from '@/shared/stores/classroom'

const props = defineProps<{ isHost: boolean; roomId: string }>()

const emit = defineEmits(['close-quiz'])
const store = useClassroomStore()

const newQuestionId = ref('Q1')
const newOptionsStr = ref('A, B, C, D')
const studentAnswer = ref<string | null>(null)

watch(() => store.activeQuiz.questionId, () => {
  studentAnswer.value = null
})

const isCorrect = computed(() => {
  if (!store.activeQuiz.correctAnswer || !studentAnswer.value) return false
  return studentAnswer.value === store.activeQuiz.correctAnswer
})

const totalResponses = computed(() => {
  if (!store.activeQuiz.stats) return 0
  return Object.values(store.activeQuiz.stats).reduce((a, b) => a + b, 0)
})

const startQuiz = () => {
  const options = newOptionsStr.value.split(',').map(s => s.trim()).filter(Boolean)
  if (options.length < 2) return
  store.startQuiz(props.roomId, newQuestionId.value, options)
}

const stopQuiz = () => {
  if (store.activeQuiz.questionId)
    store.stopQuiz(props.roomId, store.activeQuiz.questionId)
}

const setCorrectAnswer = (opt: string) => {
  if (!store.activeQuiz.questionId) return
  store.closeQuiz(props.roomId, store.activeQuiz.questionId, opt)
}

const answerAndRemember = (opt: string) => {
  if (studentAnswer.value) return
  studentAnswer.value = opt
  store.answerQuiz(props.roomId, store.activeQuiz.questionId!, opt)
}

const closeOverlay = () => {
  store.resetQuiz()
  emit('close-quiz')
}
</script>

<template>
  <template v-if="!isHost">
    <div v-if="store.activeQuiz.questionId" class="fixed inset-0 bg-zinc-950/90 backdrop-blur-sm flex flex-col items-center justify-center p-8 z-50">

      <template v-if="store.activeQuiz.isActive">
        <h3 class="text-3xl font-bold text-neutral-100 mb-8">{{ store.activeQuiz.questionId }}</h3>
        <h4 class="text-xl text-zinc-400 mb-6">Select an Answer</h4>
        <div class="grid grid-cols-2 gap-4 w-full max-w-lg">
          <button
            v-for="opt in store.activeQuiz.options"
            :key="opt"
            @click="answerAndRemember(opt)"
            class="border-2 text-3xl font-bold py-8 rounded-xl transition-all duration-200"
            :class="studentAnswer === opt 
              ? 'bg-indigo-600 border-indigo-400 text-white shadow-[0_0_20px_rgba(79,70,229,0.5)] scale-[1.02]' 
              : 'bg-zinc-800 border-zinc-700 text-neutral-200 hover:bg-neutral-200 hover:text-zinc-900 hover:border-neutral-200'"
          >
            {{ opt }}
          </button>
        </div>
        <p v-if="studentAnswer" class="mt-8 text-indigo-400 font-medium animate-pulse">
          Answer recorded! Waiting for others...
        </p>
      </template>

      <template v-else-if="!store.activeQuiz.correctAnswer">
        <div class="flex flex-col items-center gap-6">
          <div class="w-16 h-16 border-4 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin"></div>
          <div class="text-center">
            <h3 class="text-3xl font-bold text-neutral-100 mb-2">Quiz Stopped</h3>
            <p class="text-zinc-400 text-lg">The teacher is currently grading the answers...</p>
          </div>
          <div class="mt-4 px-6 py-3 bg-zinc-900 border border-zinc-800 rounded-lg">
            <p class="text-sm text-zinc-500">Your answer: <span class="font-bold text-neutral-200 text-lg ml-2">{{ studentAnswer || 'None' }}</span></p>
          </div>
        </div>
      </template>

      <template v-else>
        <div class="bg-zinc-900 border border-zinc-800 p-8 rounded-2xl max-w-sm w-full text-center shadow-2xl">
          <div class="text-7xl mb-4">{{ isCorrect ? '🎉' : '❌' }}</div>
          <h3 class="text-3xl font-bold mb-2" :class="isCorrect ? 'text-green-400' : 'text-red-400'">
            {{ isCorrect ? 'Correct!' : 'Incorrect' }}
          </h3>

          <div class="space-y-3 mt-8 mb-8 text-left bg-zinc-950 p-5 rounded-xl border border-zinc-800/80">
            <div class="flex justify-between items-center">
              <span class="text-zinc-400">Your answer</span>
              <span class="font-mono font-bold text-lg text-neutral-200">{{ studentAnswer || 'None' }}</span>
            </div>
            <div class="h-px bg-zinc-800 w-full"></div>
            <div class="flex justify-between items-center">
              <span class="text-zinc-400">Correct answer</span>
              <span class="font-mono font-bold text-lg text-green-400">{{ store.activeQuiz.correctAnswer }}</span>
            </div>
          </div>

          <button @click="closeOverlay" class="w-full py-4 bg-neutral-200 hover:bg-white text-zinc-900 font-bold text-lg rounded-xl transition shadow-lg">
            Return to Class
          </button>
        </div>
      </template>

    </div>

    <div v-if="!store.activeQuiz.questionId" class="bg-zinc-800/40 border border-zinc-800/80 rounded-lg p-4 text-center text-zinc-500 text-sm">
      No active quiz. Pay attention to the slides!
    </div>
  </template>

  <div v-if="isHost" class="absolute bottom-4 right-4 bg-zinc-900/95 border border-zinc-700 p-5 rounded-xl shadow-2xl backdrop-blur-md z-10 w-96">

    <div v-if="!store.activeQuiz.questionId">
      <div class="flex justify-between items-center mb-5">
        <span class="font-bold text-neutral-200 text-lg">Create Pop Quiz</span>
      </div>
      <div class="mb-5 space-y-4">
        <div>
          <label class="block text-xs font-bold text-zinc-500 uppercase tracking-wider mb-1.5">Question Title</label>
          <input v-model="newQuestionId" class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2.5 text-neutral-200 focus:outline-none focus:border-indigo-500 transition" placeholder="e.g., Q1" />
        </div>
        <div>
          <label class="block text-xs font-bold text-zinc-500 uppercase tracking-wider mb-1.5">Options (comma separated)</label>
          <input v-model="newOptionsStr" class="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2.5 text-neutral-200 focus:outline-none focus:border-indigo-500 transition" placeholder="A, B, C, D" />
        </div>
      </div>
      <button @click="startQuiz" class="w-full py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-bold transition shadow-lg">Start Quiz</button>
    </div>

    <div v-else>
      <div class="flex justify-between items-center mb-6">
        <span class="font-bold text-neutral-200 text-lg">
          {{ store.activeQuiz.isActive ? 'Live Responses' : (store.activeQuiz.stats ? 'Final Results' : 'Select Correct Answer') }}
        </span>
        <span 
          class="text-xs px-2 py-1 rounded font-bold"
          :class="store.activeQuiz.isActive ? 'bg-green-900/50 text-green-400 animate-pulse' : (store.activeQuiz.stats ? 'bg-indigo-900/50 text-indigo-400' : 'bg-amber-900/50 text-amber-400')"
        >
          {{ store.activeQuiz.isActive ? 'Receiving...' : (store.activeQuiz.stats ? 'Done' : 'Grading') }}
        </span>
      </div>

      <div v-if="store.activeQuiz.stats" class="space-y-3 mb-2">
        <div v-for="(count, opt) in store.activeQuiz.stats" :key="opt" class="relative flex items-center h-12">
          <div class="absolute left-0 top-0 bottom-0 rounded-md -z-10 transition-all duration-1000 ease-out" 
               :class="opt === store.activeQuiz.correctAnswer ? 'bg-green-900/40' : 'bg-zinc-800'"
               :style="{ width: `${totalResponses === 0 ? 0 : (count / totalResponses) * 100}%` }"></div>

          <div class="w-full h-full flex justify-between items-center px-3 rounded-md border"
               :class="opt === store.activeQuiz.correctAnswer ? 'border-green-500 text-green-400 bg-green-900/10' : 'border-zinc-700/50 text-neutral-200'">
            <span class="font-mono font-bold text-lg w-8">{{ opt }}</span>
            <span class="text-zinc-400 font-medium">{{ count }} votes</span>
          </div>
        </div>
        <button @click="closeOverlay" class="mt-6 w-full py-3 bg-neutral-800 hover:bg-neutral-700 text-neutral-200 rounded-lg font-bold transition">Close Panel</button>
      </div>

      <div v-else-if="!store.activeQuiz.isActive && !store.activeQuiz.correctAnswer" class="space-y-3 mb-2">
        <div v-for="opt in store.activeQuiz.options" :key="opt" class="relative flex items-center">
          <button 
            @click="setCorrectAnswer(opt)"
            class="w-full flex justify-between items-center px-4 py-3 rounded-lg border border-zinc-600 hover:bg-zinc-700 hover:border-zinc-500 text-neutral-200 cursor-pointer transition-all"
          >
            <span class="font-mono font-bold text-xl">{{ opt }}</span>
            <span class="text-zinc-400 text-sm font-medium">Set as correct</span>
          </button>
        </div>
        <p class="text-center text-sm text-zinc-500 mt-4 px-2 leading-relaxed">
          Click on an option above to set the correct answer and distribute points to students.
        </p>
      </div>

      <div v-else class="space-y-4 mb-2">
        <div class="py-8 bg-zinc-950/50 rounded-xl border border-zinc-800 flex flex-col items-center justify-center">
          <div class="w-14 h-14 border-4 border-green-500/20 border-t-green-500 rounded-full animate-spin mb-4"></div>
          <div class="text-5xl font-mono font-bold text-green-400">{{ store.activeQuiz.totalAnswered }}</div>
          <div class="text-sm text-zinc-500 font-bold uppercase tracking-widest mt-2">Answers Collected</div>
        </div>
        <button @click="stopQuiz" class="w-full py-3.5 bg-red-900/80 hover:bg-red-800 text-red-100 font-bold rounded-lg transition shadow-lg mt-2">
          Stop Quiz
        </button>
      </div>
      
    </div>
  </div>
</template>