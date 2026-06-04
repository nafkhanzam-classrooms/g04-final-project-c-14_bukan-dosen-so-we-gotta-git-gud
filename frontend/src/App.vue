<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

// Reactive state
const isConnected = ref<boolean>(false)
const messageInput = ref<string>('')
const chatHistory = ref<string[]>([])

let socket: WebSocket | null = null

// Establish connection
const connectWebSocket = (): void => {
  const wsUrl = import.meta.env.VITE_WS_URL as string

  if (!wsUrl) {
    console.error('WebSocket URL not defined in env files.')
    return
  }

  socket = new WebSocket(wsUrl)

  socket.onopen = (): void => {
    isConnected.value = true
    console.log('Connected to Python WebSocket server')
  }

  socket.onmessage = (event: MessageEvent): void => {
    // The Python server sends back a string representation of the message
    chatHistory.value.push(`Server: ${event.data}`)
  }

  socket.onclose = (): void => {
    isConnected.value = false
    console.log('Disconnected from Python WebSocket server')
  }

  socket.onerror = (error: Event): void => {
    console.error('WebSocket Error:', error)
  }
}

// Send message to Python server
const sendMessage = (): void => {
  if (socket && socket.readyState === WebSocket.OPEN && messageInput.value.trim()) {
    const textToSend = messageInput.value
    
    socket.send(textToSend)
    chatHistory.value.push(`You: ${textToSend}`)
    
    messageInput.value = '' // Clear input
  }
}

// Lifecycle hooks for clean memory management
onMounted(() => {
  connectWebSocket()
})

onUnmounted(() => {
  if (socket) {
    socket.close()
  }
})
</script>

<template>
  <div>
    <h2>Echo Client Status: 
      <span>
        {{ isConnected ? 'Connected' : 'Disconnected' }}
      </span>
    </h2>

    <div>
      <p v-if="chatHistory.length === 0">No messages yet.</p>
      <p v-for="(log, index) in chatHistory" :key="index">{{ log }}</p>
    </div>

    <form @submit.prevent="sendMessage">
      <input 
        v-model="messageInput" 
        type="text" 
        placeholder="Type a message to echo..." 
        :disabled="!isConnected"
      />
      <button type="submit" :disabled="!isConnected">Send</button>
    </form>
  </div>
</template>

<style scoped></style>
