<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useClassroomStore } from '@/shared/stores/classroom'
import LandingView from '@/features/landing/LandingView.vue'
import HostDashboardView from '@/features/host/HostDashboardView.vue'
import StudentJoinView from '@/features/join/StudentJoinView.vue'
import RoomView from '@/features/room/RoomView.vue'

type AppView = 'landing' | 'host-dashboard' | 'join' | 'room'

const store = useClassroomStore()
const currentView = ref<AppView>('landing')
const activeRoomId = ref<string | null>(null)
const activeRole = ref<'host' | 'student' | null>(null)
const activeStudentName = ref<string | null>(null)
const lastErrorMessage = ref<string>('')

function loadSession() {
  const savedRoomId = localStorage.getItem('active_room_id')
  const savedRole = localStorage.getItem('active_role') as 'host' | 'student' | null
  const savedName = localStorage.getItem('active_student_name')
  if (savedRoomId && savedRole) {
    activeRoomId.value = savedRoomId
    activeRole.value = savedRole
    activeStudentName.value = savedName
    currentView.value = 'room'
  }
}

function saveSession(roomId: string, role: 'host' | 'student', studentName?: string) {
  activeRoomId.value = roomId
  activeRole.value = role
  activeStudentName.value = studentName || null
  localStorage.setItem('active_room_id', roomId)
  localStorage.setItem('active_role', role)
  if (studentName) localStorage.setItem('active_student_name', studentName)
  else localStorage.removeItem('active_student_name')
}

function clearSession() {
  activeRoomId.value = null
  activeRole.value = null
  activeStudentName.value = null
  localStorage.removeItem('active_room_id')
  localStorage.removeItem('active_role')
  localStorage.removeItem('active_student_name')
  store.logout() // also disconnects WebSocket
}

function goToLanding() { 
  clearSession()
  lastErrorMessage.value = ''
  currentView.value = 'landing' 
}
function goToHostDashboard() { 
  clearSession()
  lastErrorMessage.value = ''
  currentView.value = 'host-dashboard' 
}
function goToJoin() { 
  clearSession()
  lastErrorMessage.value = ''
  currentView.value = 'join' 
}
function goToRoom(roomId: string, role: 'host' | 'student', studentName?: string) {
  saveSession(roomId, role, studentName)
  currentView.value = 'room'
}

watch(() => store.roomEnded, (ended) => {
  if (ended) {
    clearSession()
    currentView.value = 'landing'
  }
})
watch(() => store.lastError, (err) => {
  if (err && (err.includes('not found') || err.includes('closed'))) {
    lastErrorMessage.value = err
    if (activeRole.value === 'student') {
      clearSession()
      currentView.value = 'join'
    } else if (activeRole.value === 'host') {
      clearSession()
      currentView.value = 'host-dashboard'
    } else {
      clearSession()
      currentView.value = 'landing'
    }
  }
})

onMounted(() => {
  loadSession()
  if (activeRoomId.value && activeRole.value) {
    const name = activeRole.value === 'student' ? activeStudentName.value || 'Student' : 'Teacher'
    store.connect(activeRoomId.value, activeRole.value, name)
  }
})
</script>

<template>
  <LandingView 
    v-if="currentView === 'landing'" 
    @host="goToHostDashboard" 
    @join="goToJoin" 
  />
  <HostDashboardView 
    v-else-if="currentView === 'host-dashboard'" 
    @room-created="(roomId) => goToRoom(roomId, 'host')"
    @back="goToLanding"
  />
  <StudentJoinView 
    v-else-if="currentView === 'join'" 
    :error-message="lastErrorMessage"
    @joined="(roomId, studentName) => goToRoom(roomId, 'student', studentName)"
    @back="goToLanding"
  />
  <RoomView 
    v-else-if="currentView === 'room' && activeRoomId && activeRole"
    :room-id="activeRoomId"
    :role="activeRole"
    :student-name="activeStudentName"
    @exit="goToLanding"
  />
</template>