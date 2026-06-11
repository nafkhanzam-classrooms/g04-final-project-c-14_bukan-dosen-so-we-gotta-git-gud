<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  isHost: boolean,
  quizType: 'mcq' | 'text' | null
}>()

const emit = defineEmits(['close-quiz'])

// State: 'active' (receives answer) -> 'grading' (host/teacher picks the correct answer)
const quizState = ref<'active' | 'grading'>('active')
const selectedCorrectOption = ref<string | null>(null)

// TODO: This should come from websocket in real implementation
const answerStats = ref({ A: 12, B: 3, C: 0, D: 1 })

const stopAcceptingAnswers = () => {
  quizState.value = 'grading'
}

const finalizeGrading = (option: string) => {
  selectedCorrectOption.value = option
  // TODO: Emit the websocket to add point for the students who answered correctly
  setTimeout(() => {
    emit('close-quiz')
  }, 1500)
}
</script>

<template>
  <div v-if="!isHost" class="absolute inset-0 bg-zinc-950/90 backdrop-blur-sm flex flex-col items-center justify-center p-8 rounded-xl z-10">
    <h3 class="text-3xl font-bold text-neutral-100 mb-8">
      {{ quizType === 'mcq' ? 'Select an Answer' : 'Type your answer' }}
    </h3>
    <div v-if="quizType === 'mcq'" class="grid grid-cols-2 gap-4 w-full max-w-lg">
      <button v-for="opt in ['A', 'B', 'C', 'D']" :key="opt" class="bg-zinc-800 hover:bg-neutral-200 hover:text-zinc-900 border border-zinc-700 text-3xl font-bold py-8 rounded-xl transition">
        {{ opt }}
      </button>
    </div>
  </div>

  <div v-if="isHost" class="absolute bottom-4 right-4 bg-zinc-900/95 border border-zinc-700 p-5 rounded-xl shadow-2xl backdrop-blur-md z-10 w-96">
    <div class="flex justify-between items-center mb-6">
      <span class="font-bold text-neutral-200 text-lg">
        {{ quizState === 'active' ? 'Live Responses' : 'Select Correct Answer' }}
      </span>
      <span 
        class="text-xs px-2 py-1 rounded font-bold"
        :class="quizState === 'active' ? 'bg-green-900/50 text-green-400 animate-pulse' : 'bg-amber-900/50 text-amber-400'"
      >
        {{ quizState === 'active' ? 'Receiving...' : 'Grading' }}
      </span>
    </div>

    <div class="space-y-3 mb-6">
      <div v-for="(count, opt) in answerStats" :key="opt" class="relative flex items-center">
        <div class="absolute left-0 top-0 bottom-0 bg-zinc-800 rounded-md -z-10 transition-all duration-500" :style="{ width: `${(count / 16) * 100}%` }"></div>
        
        <button 
          @click="quizState === 'grading' ? finalizeGrading(String(opt)) : null"
          class="w-full flex justify-between items-center px-3 py-2 rounded-md border transition-all"
          :class="[
            quizState === 'grading' ? 'hover:bg-zinc-700 cursor-pointer border-zinc-600' : 'cursor-default border-transparent',
            selectedCorrectOption === opt ? 'bg-green-900/50 border-green-500 text-green-400' : 'text-neutral-200'
          ]"
        >
          <span class="font-mono font-bold text-lg w-8">{{ opt }}</span>
          <span class="text-zinc-400 font-medium">{{ count }} votes</span>
        </button>
      </div>
    </div>

    <button v-if="quizState === 'active'" @click="stopAcceptingAnswers" class="w-full py-3 bg-red-900/80 hover:bg-red-800 text-red-100 font-bold rounded-lg transition shadow-lg">
      Stop Quiz
    </button>
    <p v-else class="text-center text-sm text-zinc-500">
      {{ selectedCorrectOption ? 'Distributing points...' : 'Click on a bar above to set the correct answer.' }}
    </p>
  </div>
</template>