<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useClassroomStore } from '@/shared/stores/classroom'
import { storeToRefs } from 'pinia'
import LandingView from '@/features/landing/LandingView.vue'
import HostDashboardView from '@/features/host/HostDashboardView.vue'
import StudentJoinView from '@/features/join/StudentJoinView.vue'
import RoomView from '@/features/room/RoomView.vue'

type AppView = 'landing' | 'host-dashboard' | 'join' | 'room'

const store = useClassroomStore()
const { lastError } = storeToRefs(store)
const currentView = ref<AppView>('landing')
const activeRoomId = ref<string | null>(null)
const activeRole = ref<'host' | 'student' | null>(null)
const activeStudentName = ref<string | null>(null)

const joinErrorMessage = ref<string | null>(null)
const hostErrorMessage = ref<string | null>(null)

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
  store.logout() 
}

function goToLanding() {
  clearSession()
  joinErrorMessage.value = null
  hostErrorMessage.value = null
  currentView.value = 'landing'
}
function goToHostDashboard() {
  clearSession()
  joinErrorMessage.value = null
  hostErrorMessage.value = null
  currentView.value = 'host-dashboard'
}
function goToJoin() {
  clearSession()
  joinErrorMessage.value = null
  hostErrorMessage.value = null
  currentView.value = 'join'
}
function goToRoom(roomId: string, role: 'host' | 'student', studentName?: string) {
  saveSession(roomId, role, studentName)
  const designatedName = role === 'host' ? 'Teacher' : (studentName || 'Student')
  store.connect(roomId, role, designatedName)
  currentView.value = 'room'
}

watch(lastError, (err) => {
  if (!err) return

  console.error('[App] Error detected in store:', err)
  console.log('[App] Current role before clear:', activeRole.value)
  
  const previousRole = activeRole.value 
  clearSession()

  if (previousRole === 'student') {
    console.log('[App] Redirecting student to join view with error:', err)
    joinErrorMessage.value = err
    currentView.value = 'join'
  } else if (previousRole === 'host') {
    console.log('[App] Redirecting host to dashboard with error:', err)
    hostErrorMessage.value = err
    currentView.value = 'host-dashboard'
  } else {
    console.log('[App] Redirecting to landing')
    currentView.value = 'landing'
  }
}, { immediate: false, flush: 'sync' })

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
    :error-message="joinErrorMessage || undefined"
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