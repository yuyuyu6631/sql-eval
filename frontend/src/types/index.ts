export interface SchemaEnv {
  id: number
  env_name: string
  ddl_content: string
  sandbox_db_url?: string
  created_at: string
  updated_at: string
}

export interface TestCase {
  id: number
  env_id: number
  question: string
  golden_sql: string
  tags: string[]
  created_at: string
  updated_at: string
}

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

export interface EvaluationTask {
  id: number
  task_name: string
  agent_id: number
  env_id: number
  case_ids: number[]
  judge_llm_model?: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  stats_json?: TaskStats
  created_at: string
  completed_at?: string
}

export interface TaskStats {
  total: number
  passed: number
  failed: number
  errors: number
  pass_rate: number
}

export interface EvaluationResult {
  id: number
  task_id: number
  case_id: number
  agent_sql?: string
  execution_status: string
  golden_data?: any[]
  agent_data?: any[]
  data_diff_passed: boolean
  ai_diagnosis?: string
  execution_time_ms?: number
  error_message?: string
  created_at: string
}

export interface DashboardStats {
  total_tasks: number
  total_cases: number
  total_results: number
  status_counts: Record<string, number>
  pass_rate: number
}
