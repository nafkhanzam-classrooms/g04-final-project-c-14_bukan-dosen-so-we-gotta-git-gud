<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <div class="flex flex-col items-center justify-center h-full px-6">
    <div class="text-center max-w-2xl">
      <h1 class="text-5xl font-extrabold text-neutral-100 tracking-tight mb-4">
        Interactive Classrooms
      </h1>
      <p class="text-lg text-zinc-400 mb-10">
        Engage your students with real-time slides, live quizzes, and instant feedback.
      </p>
      
      <div class="flex flex-col sm:flex-row gap-4 justify-center">
        <button 
          @click="router.push('/join')"
          class="px-8 py-4 bg-neutral-100 text-zinc-950 font-bold rounded-xl hover:bg-neutral-300 transition shadow-lg"
        >
          Join as Student
        </button>
        <button 
          @click="router.push('/host')"
          class="px-8 py-4 bg-zinc-800 text-neutral-200 font-bold rounded-xl border border-zinc-700 hover:bg-zinc-700 hover:text-neutral-100 transition shadow-lg"
        >
          Host a Class
        </button>
      </div>
    </div>
  </div>
</template>