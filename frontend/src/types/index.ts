/* ============================================================
   前端类型声明（与后端 Pydantic Schema 严格对应）
   使用 snake_case 与后端保持一致，减少转换开销
   ============================================================ */

/* ---- Schema 环境 ---- */
export interface SchemaEnv {
  id: number
  env_name: string
  ddl_content: string
  sandbox_db_url?: string
  created_at: string
  updated_at: string
}

/* ---- 测试用例 ---- */
export interface TestCase {
  id: number
  env_id: number
  question: string
  golden_sql: string
  tags: string[]
  created_at: string
  updated_at: string
}

/* ---- Agent 配置 ---- */
export interface AgentConfig {
  id: number
  agent_name: string
  api_endpoint: string
  auth_token?: string
  rate_limit_qps: number
  timeout_ms: number
  created_at: string
  updated_at: string
}

/* ---- 任务状态枚举 ---- */
export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed'

/* ---- 任务统计 ---- */
export interface TaskStats {
  total: number
  passed: number
  failed: number
  errors: number
  pass_rate: number
}

/* ---- 评估任务 ---- */
export interface EvaluationTask {
  id: number
  task_name: string
  agent_id: number
  env_id: number
  case_ids: number[]
  judge_llm_model?: string
  status: TaskStatus
  stats_json?: TaskStats
  created_at: string
  completed_at?: string
}

/* ---- 评估结果 ---- */
export interface EvaluationResult {
  id: number
  task_id: number
  case_id: number
  agent_sql?: string
  execution_status: string
  golden_data?: Record<string, unknown>[]
  agent_data?: Record<string, unknown>[]
  data_diff_passed: boolean
  ai_diagnosis?: string
  execution_time_ms?: number
  error_message?: string
  created_at: string
}

/* ---- Dashboard 统计 ---- */
export interface DashboardStats {
  total_tasks: number
  total_cases: number
  total_results: number
  status_counts: Record<string, number>
  pass_rate: number
}

/* ---- 复杂度分析（新增）---- */
export interface ComplexityAnalysis {
  avg_execution_time_ms: number
  slowest_query_ms: number
  fastest_query_ms: number
  total_queries: number
}

/* ---- 错误分布（新增）---- */
export interface ErrorDistribution {
  distribution: Record<string, number>
}

/* ---- 任务进度（新增）---- */
export interface TaskProgressResponse {
  task_id: number
  status: TaskStatus
  total_cases: number
  completed_cases: number
  progress_percentage: number
}

/* ---- 排行榜条目（新增）---- */
export interface LeaderboardItem {
  agent_id: number
  total_tests: number
  passed: number
  pass_rate: number
}

/* ---- 排行榜响应（新增）---- */
export interface LeaderboardResponse {
  leaderboard: LeaderboardItem[]
}

/* ---- AI 诊断（新增）---- */
export interface DiagnosisResponse {
  result_id: number
  diagnosis?: string
}

export interface JudgeConfig {
  endpoint?: string
  default_model?: string
  api_key_configured: boolean
}

export interface JudgeConfigTestResult {
  ok: boolean
  model: string
  preview: string
}
