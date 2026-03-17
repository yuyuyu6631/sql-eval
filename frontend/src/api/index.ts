import axios from 'axios'
import type {
  SchemaEnv,
  TestCase,
  AgentConfig,
  EvaluationTask,
  EvaluationResult,
  DashboardStats,
} from '../types'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000, // 增加 10s 超时防止界面无响应
})

// 响应拦截器：统一处理错误提示，解决“无响应”后的迷茫
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === 'ECONNABORTED') {
      window.console.error('API Timeout - Interface Unresponsive Fix');
    }
    return Promise.reject(error);
  }
)

// Environment APIs
export const getSchemaEnvs = () => api.get<SchemaEnv[]>('/schema-envs')
export const getSchemaEnv = (id: number) => api.get<SchemaEnv>(`/schema-envs/${id}`)
export const createSchemaEnv = (data: Partial<SchemaEnv>) =>
  api.post<SchemaEnv>('/schema-envs', data)
export const updateSchemaEnv = (id: number, data: Partial<SchemaEnv>) =>
  api.put<SchemaEnv>(`/schema-envs/${id}`, data)
export const deleteSchemaEnv = (id: number) => api.delete(`/schema-envs/${id}`)

// Test Case APIs
export const getTestCases = (envId?: number) =>
  api.get<TestCase[]>('/test-cases', { params: { env_id: envId } })
export const getTestCase = (id: number) => api.get<TestCase>(`/test-cases/${id}`)
export const createTestCase = (data: Partial<TestCase>) =>
  api.post<TestCase>('/test-cases', data)
export const createTestCasesBatch = (data: Partial<TestCase>[]) =>
  api.post<TestCase[]>('/test-cases/batch', data)
export const updateTestCase = (id: number, data: Partial<TestCase>) =>
  api.put<TestCase>(`/test-cases/${id}`, data)
export const deleteTestCase = (id: number) => api.delete(`/test-cases/${id}`)
export const generateTestCases = (data: { env_id: number; count: number }) =>
  api.post<TestCase[]>('/test-cases/generate', data)

// Agent APIs
export const getAgents = () => api.get<AgentConfig[]>('/agents')
export const getAgent = (id: number) => api.get<AgentConfig>(`/agents/${id}`)
export const createAgent = (data: Partial<AgentConfig>) =>
  api.post<AgentConfig>('/agents', data)
export const updateAgent = (id: number, data: Partial<AgentConfig>) =>
  api.put<AgentConfig>(`/agents/${id}`, data)
export const deleteAgent = (id: number) => api.delete(`/agents/${id}`)

// Task APIs
export const getTasks = (status?: string) =>
  api.get<EvaluationTask[]>('/tasks', { params: { status_filter: status } })
export const getTask = (id: number) => api.get<EvaluationTask>(`/tasks/${id}`)
export const createTask = (data: Partial<EvaluationTask>) =>
  api.post<EvaluationTask>('/tasks', data)
export const updateTask = (id: number, data: Partial<EvaluationTask>) =>
  api.put<EvaluationTask>(`/tasks/${id}`, data)
export const deleteTask = (id: number) => api.delete(`/tasks/${id}`)
export const startTask = (id: number) => api.post(`/tasks/${id}/start`)
export const getTaskProgress = (id: number) =>
  api.get(`/tasks/${id}/progress`)

// Result APIs
export const getResults = (taskId?: number, caseId?: number) =>
  api.get<EvaluationResult[]>('/results', {
    params: { task_id: taskId, case_id: caseId },
  })
export const getResult = (id: number) => api.get<EvaluationResult>(`/results/${id}`)
export const getDiagnosis = (resultId: number) =>
  api.get(`/results/${resultId}/diagnosis`)

// Dashboard APIs
export const getDashboardStats = () => api.get<DashboardStats>('/dashboard/stats')
export const getErrorDistribution = () => api.get('/dashboard/error-distribution')
export const getComplexityAnalysis = () => api.get('/dashboard/complexity-analysis')
export const getLeaderboard = () => api.get('/dashboard/leaderboard')

export default api
