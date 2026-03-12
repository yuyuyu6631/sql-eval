import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'Dashboard',
      component: () => import('../views/Dashboard.vue'),
    },
    {
      path: '/environments',
      name: 'Environments',
      component: () => import('../views/EnvironmentConfig.vue'),
    },
    {
      path: '/test-cases',
      name: 'TestCases',
      component: () => import('../views/TestCaseManage.vue'),
    },
    {
      path: '/agents',
      name: 'Agents',
      component: () => import('../views/AgentConfig.vue'),
    },
    {
      path: '/tasks',
      name: 'Tasks',
      component: () => import('../views/TaskExecution.vue'),
    },
  ],
})

export default router
