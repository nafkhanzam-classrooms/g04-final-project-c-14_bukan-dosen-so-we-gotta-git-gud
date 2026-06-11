<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const isGenerating = ref(false)

const createRoom = () => {
  isGenerating.value = true
  setTimeout(() => {
    const newRoomCode = Math.random().toString(36).substring(2, 8).toUpperCase()
    router.push(`/room/${newRoomCode}?role=host`)
  }, 1000)
}
</script>

<template>
  <div class="p-8 max-w-5xl mx-auto h-full flex flex-col pt-20">
    <div class="bg-zinc-900 border border-zinc-800 p-10 rounded-2xl shadow-2xl text-center">
      <h1 class="text-3xl font-bold text-neutral-100 mb-4">Teacher Dashboard</h1>
      <p class="text-zinc-400 mb-10 max-w-lg mx-auto">
        Create a new session, upload your presentation, and invite your students to join interactively.
      </p>
      
      <button 
        @click="createRoom" 
        :disabled="isGenerating"
        class="bg-neutral-100 text-zinc-950 px-10 py-4 rounded-xl font-bold text-lg hover:bg-neutral-300 transition disabled:opacity-50 disabled:cursor-not-allowed shadow-lg"
      >
        {{ isGenerating ? 'Initializing...' : 'Create New Class' }}
      </button>
    </div>
  </div>
</template>