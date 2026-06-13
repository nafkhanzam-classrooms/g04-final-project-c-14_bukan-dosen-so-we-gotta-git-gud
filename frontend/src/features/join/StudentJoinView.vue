<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()
const roomCode = ref('')
const username = ref('')
const errorMessage = ref('')

onMounted(() => {
  if (route.query.error) {
    errorMessage.value = route.query.error as string
    router.replace({ path: '/join', query: {} })
    setTimeout(() => {
      errorMessage.value = ''
    }, 5000)
  }
})

const joinRoom = () => {
  if (roomCode.value && username.value) {
    router.push(`/room/${roomCode.value.toUpperCase()}?studentName=${encodeURIComponent(username.value)}`)
  }
}
</script>

<template>
  <button @click="router.push('/')" class="text-zinc-400 hover:text-neutral-200 text-sm absolute top-4 left-4">
    ← Back to Home
  </button>
  <div class="flex flex-col items-center justify-center h-full px-6">
    <div class="w-full max-w-md bg-zinc-900 border border-zinc-800 p-8 rounded-2xl shadow-2xl">
      <div class="flex justify-end mb-2">
      </div>
      <div v-if="errorMessage" class="mb-4 p-3 bg-red-900/50 border border-red-700 rounded-lg text-red-200 text-sm">
        {{ errorMessage }}
      </div>
      <h1 class="text-2xl font-bold text-neutral-100 mb-6 text-center">Join Session</h1>
      
      <form @submit.prevent="joinRoom" class="space-y-5">
        <div>
          <label class="block text-sm font-medium text-zinc-400 mb-1">Room Code</label>
          <input 
            v-model="roomCode" 
            type="text" 
            class="w-full bg-zinc-950 border border-zinc-800 text-neutral-200 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-neutral-500 uppercase transition"
            placeholder="XYZ123" 
            required 
          />
        </div>
        
        <div>
          <label class="block text-sm font-medium text-zinc-400 mb-1">Display Name</label>
          <input 
            v-model="username" 
            type="text" 
            class="w-full bg-zinc-950 border border-zinc-800 text-neutral-200 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-neutral-500 transition"
            placeholder="John Doe" 
            required 
          />
        </div>

        <button 
          type="submit" 
          class="w-full bg-neutral-100 text-zinc-950 font-bold py-3 rounded-lg hover:bg-neutral-300 transition mt-2"
        >
          Enter Room
        </button>
      </form>
    </div>
  </div>
</template>