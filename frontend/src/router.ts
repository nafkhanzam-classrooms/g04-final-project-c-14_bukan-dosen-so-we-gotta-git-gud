import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'landing',
      component: () => import('@/features/landing/LandingView.vue'),
    },
    {
      path: '/join',
      name: 'join',
      component: () => import('@/features/join/StudentJoinView.vue'),
    },
    {
      path: '/host',
      name: 'host',
      component: () => import('@/features/host/HostDashboardView.vue'),
    },
    {
      path: '/room/:roomId',
      name: 'room',
      component: () => import('@/features/room/RoomView.vue'),
    },
  ],
})

export default router
