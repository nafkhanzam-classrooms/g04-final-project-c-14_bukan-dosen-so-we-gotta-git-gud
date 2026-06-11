<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  students: Array<{ name: string, score: number }>
}>()

const sortedStudents = computed(() => {
  return [...props.students].sort((a, b) => b.score - a.score)
})
</script>

<template>
  <div class="flex-1 flex flex-col items-center justify-center p-10 overflow-y-auto">
    <h1 class="text-5xl font-extrabold text-neutral-100 mb-2">Session Ended</h1>
    <p class="text-xl text-zinc-400 mb-10">Final Leaderboard</p>
    
    <div class="w-full max-w-lg bg-zinc-900 border border-zinc-800 rounded-2xl shadow-2xl overflow-hidden">
      <div 
        v-for="(student, index) in sortedStudents" 
        :key="student.name"
        class="flex items-center justify-between p-6 border-b border-zinc-800/50 last:border-0"
        :class="{'bg-zinc-800/30': index === 0}"
      >
        <div class="flex items-center gap-4">
          <div 
            class="w-10 h-10 rounded-full flex items-center justify-center font-bold text-lg"
            :class="index === 0 ? 'bg-yellow-500/20 text-yellow-500' : index === 1 ? 'bg-zinc-300/20 text-zinc-300' : index === 2 ? 'bg-amber-700/20 text-amber-500' : 'bg-zinc-800 text-zinc-500'"
          >
            {{ index + 1 }}
          </div>
          <span class="text-lg font-semibold text-neutral-200">{{ student.name }}</span>
        </div>
        <span class="text-2xl font-bold text-neutral-100">{{ student.score }} <span class="text-sm text-zinc-500 font-normal">pts</span></span>
      </div>
    </div>
  </div>
</template>