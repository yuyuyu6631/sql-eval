<template>
  <div class="task-page">
    <!-- 顶部工具栏 -->
    <div class="page-toolbar">
      <h1 class="page-heading">{{ t('task.title') }}</h1>
      <button class="m-btn primary" @click="showCreateDialog" aria-label="创建新评估任务">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        {{ t('task.createTask') }}
      </button>
    </div>

    <!-- 任务列表 -->
    <div class="m-card tasks-card">
      <!-- 骨架屏 -->
      <template v-if="isLoadingTasks">
        <div v-for="i in 3" :key="i" class="m-skeleton" style="height: 52px; margin-bottom: 10px; border-radius: 8px;"></div>
      </template>

      <!-- 空状态 -->
      <div v-else-if="tasks.length === 0" class="m-empty">
        <div class="m-empty-icon" aria-hidden="true">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
        </div>
        <div class="m-empty-title">{{ t('task.noTasks') }}</div>
        <div class="m-empty-desc">{{ t('task.noTasksDesc') }}</div>
      </div>

      <!-- 任务列表 -->
      <div v-else class="task-list" role="list">
        <div
          v-for="task in tasks"
          :key="task.id"
          class="task-item"
          role="listitem"
        >
          <!-- 状态指示 -->
          <div class="task-status-col">
            <span
              class="m-tag"
              :class="statusTagClass(task.status)"
              :aria-label="`任务状态: ${task.status}`"
            >
              <!-- 运行中显示 spinner -->
              <span v-if="task.status === 'running'" class="m-spinner" style="width:10px;height:10px;border-width:1.5px;" aria-hidden="true"></span>
              {{ task.status }}
            </span>
          </div>

          <!-- 主信息 -->
          <div class="task-info">
            <div class="task-name">{{ task.task_name }}</div>
            <div class="task-meta">
              Agent #{{ task.agent_id }} · Env #{{ task.env_id }} · {{ formatDate(task.created_at) }}
            </div>
          </div>

          <!-- 进度 -->
          <div class="task-progress-col">
            <div v-if="task.stats_json" class="task-stat">
              <span class="stat-pass">{{ task.stats_json.passed }}</span>
              <span class="stat-sep">/</span>
              <span class="stat-total">{{ task.stats_json.total }}</span>
              <span class="stat-rate">({{ task.stats_json.pass_rate }}%)</span>
            </div>
            <!-- 运行中任务的进度条 -->
            <div v-if="task.status === 'running' && taskProgress[task.id]" class="inline-progress" role="progressbar" :aria-valuenow="taskProgress[task.id]?.progress_percentage" :aria-valuemax="100">
              <div class="inline-progress-fill" :style="{ width: taskProgress[task.id]?.progress_percentage + '%' }"></div>
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="task-actions">
            <!-- 启动按钮：运行中禁用 + loading 防重复 -->
            <button
              class="m-btn sm primary"
              :class="{ 'is-loading': startingTasks.has(task.id) }"
              :disabled="task.status === 'running' || task.status === 'completed'"
              @click="handleStartTask(task.id)"
              :aria-label="`启动任务 ${task.task_name}`"
            >
              <span v-if="startingTasks.has(task.id)" class="m-spinner" aria-hidden="true"></span>
              <span v-else aria-hidden="true">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
              </span>
              {{ t('task.run') }}
            </button>

            <button
              class="m-btn sm secondary"
              @click="handleViewResults(task)"
              :aria-label="`查看任务 ${task.task_name} 的结果`"
            >
              {{ t('task.viewDetail') }}
            </button>

            <button
              class="m-btn sm danger"
              @click="handleDeleteTask(task.id)"
              :aria-label="`删除任务 ${task.task_name}`"
            >
              {{ t('common.delete') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 创建任务对话框 -->
    <el-dialog v-model="dialogVisible" :title="t('task.createTask')" width="480px">
      <el-form :model="form" label-width="110px">
        <el-form-item :label="t('task.name')" required>
          <el-input v-model="form.task_name" :placeholder="t('task.namePlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('common.agents')" required>
          <el-select v-model="form.agent_id" :placeholder="t('env.placeholder')" style="width:100%">
            <el-option v-for="agent in agents" :key="agent.id" :label="agent.agent_name" :value="agent.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('common.environment')" required>
          <el-select v-model="form.env_id" :placeholder="t('env.placeholder')" style="width:100%">
            <el-option v-for="env in environments" :key="env.id" :label="env.env_name" :value="env.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="Case IDs">
          <el-input v-model="caseIdsInput" placeholder="留空则使用全部用例，多个 ID 用逗号分隔" />
        </el-form-item>
        <el-form-item :label="t('task.judgeModel')">
          <el-input v-model="form.judge_llm_model" placeholder="Optional: gpt-4o" />
        </el-form-item>
      </el-form>
      <template #footer>
        <button class="m-btn secondary" @click="dialogVisible = false">{{ t('common.cancel') }}</button>
        <button class="m-btn primary" :class="{ 'is-loading': isSubmitting }" @click="submitCreate" style="margin-left: 8px;">
          <span v-if="isSubmitting" class="m-spinner" aria-hidden="true"></span>
          {{ t('common.add') }}
        </button>
      </template>
    </el-dialog>

    <!-- 结果详情对话框 -->
    <el-dialog v-model="resultsVisible" :title="t('task.viewDetail')" width="90%" top="5vh">
      <div v-if="selectedTask">
        <!-- 汇总 Tag 行 -->
        <div class="result-summary-row">
          <span class="m-tag success">{{ t('common.success') }}: {{ selectedTask.stats_json?.passed ?? 0 }}</span>
          <span class="m-tag danger">{{ t('common.failed') }}: {{ selectedTask.stats_json?.failed ?? 0 }}</span>
          <span class="m-tag neutral">Total: {{ selectedTask.stats_json?.total ?? 0 }}</span>
        </div>

        <!-- 结果表格 -->
        <el-table :data="results" max-height="350" highlight-current-row @row-click="handleRowClick" style="cursor: pointer;">
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column prop="case_id" label="Case ID" width="90" />
          <el-table-column prop="agent_sql" :label="t('task.agentSql')" show-overflow-tooltip />
          <el-table-column prop="execution_status" :label="t('task.status')" width="130">
            <template #default="{ row }">
              <span class="m-tag" :class="row.data_diff_passed ? 'success' : 'danger'">
                {{ row.execution_status }}
              </span>
            </template>
          </el-table-column>
          <el-table-column :label="t('task.dataDiff')" width="90">
            <template #default="{ row }">
              <span class="m-tag" :class="row.data_diff_passed ? 'success' : 'danger'">
                {{ row.data_diff_passed ? 'PASS' : 'FAIL' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column :label="t('task.actions')" width="130">
            <template #default="{ row }">
              <button class="m-btn sm ghost" @click.stop="handleViewDiagnosis(row)">
                {{ t('task.diagnosis') }}
              </button>
            </template>
          </el-table-column>
        </el-table>

        <!-- SQL Diff 对比区 -->
        <div v-if="currentResult" class="sql-diff-section">
          <div class="diff-header">
            <span class="diff-title">SQL {{ t('task.sqlDiff') }}</span>
            <span class="m-tag" :class="currentResult.data_diff_passed ? 'success' : 'danger'">
              {{ currentResult.data_diff_passed ? 'MATCH' : 'MISMATCH' }}
            </span>
          </div>
          <div class="diff-panels">
            <div class="diff-panel">
              <div class="diff-panel-label">{{ t('task.goldenSql') }}</div>
              <pre class="m-code">{{ getGoldenSql(currentResult.case_id) }}</pre>
            </div>
            <div class="diff-panel" :class="{ 'panel-error': !currentResult.data_diff_passed }">
              <div class="diff-panel-label">{{ t('task.agentSql') }}</div>
              <pre class="m-code" :class="{ 'code-error': !currentResult.data_diff_passed }">{{ currentResult.agent_sql ?? '（无输出）' }}</pre>
            </div>
          </div>

          <!-- AI 诊断展开 -->
          <div v-if="currentResult.ai_diagnosis" class="diagnosis-block">
            <button class="m-btn sm ghost diag-toggle" @click="showDiagnosis = !showDiagnosis">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
              AI 诊断
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" :style="{ transform: showDiagnosis ? 'rotate(180deg)' : 'none', transition: 'transform 200ms' }" aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg>
            </button>
            <div v-show="showDiagnosis" class="diagnosis-content">
              <pre class="m-code">{{ currentResult.ai_diagnosis }}</pre>
            </div>
          </div>

          <!-- 错误信息 -->
          <div v-if="currentResult.error_message" class="error-block">
            <div class="error-label">错误信息</div>
            <pre class="m-code code-error">{{ currentResult.error_message }}</pre>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import type { EvaluationTask, EvaluationResult, AgentConfig, SchemaEnv, TaskProgressResponse } from '../types'
import {
  getTasks, createTask, deleteTask,
  startTask as apiStartTask,
  getTaskProgress,
  getResults,
  getAgents, getSchemaEnvs,
  getTestCases,
} from '../api'
import { t } from '../i18n'
import api from '../api'

/* ---- 状态 ---- */
const tasks             = ref<EvaluationTask[]>([])
const results           = ref<EvaluationResult[]>([])
const agents            = ref<AgentConfig[]>([])
const environments      = ref<SchemaEnv[]>([])
const selectedTask      = ref<EvaluationTask | null>(null)
const currentResult     = ref<EvaluationResult | null>(null)
const testCaseMap       = ref<Record<number, string>>({})
const isLoadingTasks    = ref(true)
const isSubmitting      = ref(false)
const dialogVisible     = ref(false)
const resultsVisible    = ref(false)
const showDiagnosis     = ref(false)

/** 正在启动中的任务 ID 集合（防重复点击） */
const startingTasks = ref<Set<number>>(new Set())

/** 各运行中任务的进度数据 */
const taskProgress = ref<Record<number, TaskProgressResponse>>({})

const form = ref({
  task_name: '',
  agent_id: undefined as number | undefined,
  env_id: undefined as number | undefined,
  judge_llm_model: '',
})
const caseIdsInput = ref('')

/* ---- 轮询机制 ---- */
let pollingTimer: ReturnType<typeof setInterval> | null = null

const startPolling = () => {
  if (pollingTimer) return
  pollingTimer = setInterval(async () => {
    const runningTasks = tasks.value.filter(t => t.status === 'running')
    if (runningTasks.length === 0) return

    // 并行拉取所有运行中任务的进度
    await Promise.allSettled(
      runningTasks.map(async (task) => {
        try {
          const res = await getTaskProgress(task.id)
          taskProgress.value[task.id] = res.data
          // 若已完成，刷新任务列表，停止单独追踪
          if (res.data.status !== 'running') {
            await refreshTasks()
          }
        } catch { /* 忽略单条失败 */ }
      })
    )
  }, 5000) // 每 5 秒轮询一次
}

const stopPolling = () => {
  if (pollingTimer) {
    clearInterval(pollingTimer)
    pollingTimer = null
  }
}

/* ---- 数据加载 ---- */
const refreshTasks = async () => {
  const res = await getTasks()
  tasks.value = res.data
}

const loadTasks = async () => {
  isLoadingTasks.value = true
  try {
    await refreshTasks()
  } catch {
    ElMessage.error(t('common.failed'))
  } finally {
    isLoadingTasks.value = false
  }
}

/* ---- 操作 ---- */
const showCreateDialog = () => {
  form.value = { task_name: '', agent_id: undefined, env_id: undefined, judge_llm_model: '' }
  caseIdsInput.value = ''
  dialogVisible.value = true
}

const submitCreate = async () => {
  if (!form.value.task_name || !form.value.agent_id || !form.value.env_id) {
    ElMessage.warning('请填写必填项')
    return
  }
  isSubmitting.value = true
  try {
    const data: Record<string, unknown> = { ...form.value }
    if (caseIdsInput.value) {
      data.case_ids = caseIdsInput.value.split(',').map(s => parseInt(s.trim())).filter(n => !isNaN(n))
    }
    await createTask(data)
    ElMessage.success(t('task.createSuccess'))
    dialogVisible.value = false
    await refreshTasks()
  } catch {
    ElMessage.error(t('common.failed'))
  } finally {
    isSubmitting.value = false
  }
}

const handleStartTask = async (id: number) => {
  if (startingTasks.value.has(id)) return
  startingTasks.value = new Set([...startingTasks.value, id])
  try {
    await apiStartTask(id)
    ElMessage.success(t('common.success'))
    await refreshTasks()
  } catch {
    ElMessage.error(t('common.failed'))
  } finally {
    const s = new Set(startingTasks.value)
    s.delete(id)
    startingTasks.value = s
  }
}

const handleDeleteTask = async (id: number) => {
  try {
    await deleteTask(id)
    ElMessage.success(t('common.success'))
    await refreshTasks()
  } catch {
    ElMessage.error(t('common.failed'))
  }
}

const handleViewResults = async (task: EvaluationTask) => {
  selectedTask.value = task
  currentResult.value = null
  showDiagnosis.value = false
  try {
    const [resRes, caseRes] = await Promise.all([
      getResults(task.id),
      api.get('/test-cases', { params: { env_id: task.env_id } }),
    ])
    results.value = resRes.data
    testCaseMap.value = (caseRes.data as { id: number; golden_sql: string }[])
      .reduce<Record<number, string>>((acc, c) => { acc[c.id] = c.golden_sql; return acc }, {})
    resultsVisible.value = true
  } catch {
    ElMessage.error(t('common.failed'))
  }
}

const handleRowClick = (row: EvaluationResult) => {
  currentResult.value = row
  showDiagnosis.value = false
}

const getGoldenSql = (caseId: number): string =>
  testCaseMap.value[caseId] ?? '加载中...'

const handleViewDiagnosis = async (result: EvaluationResult) => {
  currentResult.value = result
  showDiagnosis.value = true
}

/* ---- 工具函数 ---- */
const statusTagClass = (status: string): string => ({
  pending:   'warning',
  running:   'info',
  completed: 'success',
  failed:    'danger',
}[status] ?? 'neutral')

const formatDate = (d: string) => new Date(d).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })

/* ---- 生命周期 ---- */
onMounted(async () => {
  await Promise.all([
    loadTasks(),
    getAgents().then(r => agents.value = r.data),
    getSchemaEnvs().then(r => environments.value = r.data),
  ])
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.task-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
  animation: fade-in 200ms ease-out;
}

@keyframes fade-in { from { opacity: 0; } to { opacity: 1; } }

.page-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.page-heading {
  font-size: 20px;
  font-weight: 700;
  color: var(--m-text);
}

/* ---- 任务卡片 ---- */
.tasks-card {
  padding: 16px;
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.task-item {
  display: grid;
  grid-template-columns: 110px 1fr auto auto;
  align-items: center;
  gap: 16px;
  padding: 14px 16px;
  border: 1px solid var(--m-border);
  border-radius: var(--radius-lg);
  transition: background-color var(--t-fast), border-color var(--t-fast);
}

.task-item:hover {
  background: var(--m-surface-hover);
  border-color: var(--m-border-strong);
}

.task-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--m-text);
}

.task-meta {
  font-size: 12px;
  color: var(--m-text-muted);
  margin-top: 3px;
}

.task-progress-col {
  min-width: 120px;
}

.task-stat {
  font-size: 13px;
  font-family: var(--font-mono);
  color: var(--m-text-muted);
}

.stat-pass { color: var(--m-primary); font-weight: 700; }
.stat-sep  { margin: 0 2px; }
.stat-rate { font-size: 11px; margin-left: 4px; color: var(--m-text-dim); }

.inline-progress {
  height: 3px;
  background: var(--m-surface-bright);
  border-radius: 2px;
  margin-top: 6px;
  overflow: hidden;
}

.inline-progress-fill {
  height: 100%;
  background: var(--m-info);
  border-radius: 2px;
  transition: width var(--t-slow);
  animation: progress-shimmer 1.5s ease-in-out infinite;
}

@keyframes progress-shimmer {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

@media (prefers-reduced-motion: reduce) {
  .inline-progress-fill { animation: none; }
}

.task-actions {
  display: flex;
  gap: 6px;
  align-items: center;
}

/* ---- 结果弹窗 ---- */
.result-summary-row {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}

/* SQL Diff */
.sql-diff-section {
  margin-top: 20px;
  border-top: 1px solid var(--m-border);
  padding-top: 20px;
}

.diff-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.diff-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--m-text);
}

.diff-panels {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.diff-panel {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.diff-panel-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--m-text-muted);
}

.diff-panel.panel-error .diff-panel-label {
  color: var(--m-danger);
}

.m-code.code-error {
  border-color: rgba(239, 68, 68, 0.3);
  color: #fca5a5; /* rose-300 */
}

/* AI 诊断 */
.diagnosis-block {
  margin-top: 16px;
  border-top: 1px solid var(--m-border);
  padding-top: 16px;
}

.diag-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
}

/* 错误信息 */
.error-block {
  margin-top: 16px;
}

.error-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--m-danger);
  margin-bottom: 6px;
}
</style>
