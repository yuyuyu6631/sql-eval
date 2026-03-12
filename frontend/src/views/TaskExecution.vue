<template>
  <div class="task-execution">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ t('task.title') }}</span>
          <el-button type="primary" @click="showCreateDialog">{{ t('task.createTask') }}</el-button>
        </div>
      </template>

      <el-table :data="tasks" v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="task_name" :label="t('task.name')" />
        <el-table-column prop="agent_id" :label="t('task.agentId')" width="100" />
        <el-table-column prop="env_id" :label="t('task.envId')" width="100" />
        <el-table-column prop="status" :label="t('task.status')" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('task.stats')" width="180">
          <template #default="{ row }">
            <span v-if="row.stats_json">
              {{ row.stats_json.passed || 0 }}/{{ row.stats_json.total || 0 }}
              ({{ row.stats_json.pass_rate || 0 }}%)
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" :label="t('task.startTime')" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column :label="t('task.actions')" width="250">
          <template #default="{ row }">
            <el-button size="small" type="success" :disabled="row.status === 'running'" @click="startTask(row.id)">
              {{ t('task.run') }}
            </el-button>
            <el-button size="small" @click="viewResults(row)">{{ t('task.viewDetail') }}</el-button>
            <el-button size="small" type="danger" @click="deleteTaskById(row.id)">{{ t('common.delete') }}</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="t('task.createTask')" width="500px">
      <el-form :model="form" label-width="120px">
        <el-form-item :label="t('task.name')">
          <el-input v-model="form.task_name" :placeholder="t('env.placeholder')" />
        </el-form-item>
        <el-form-item :label="t('common.agents')">
          <el-select v-model="form.agent_id" :placeholder="t('env.placeholder')">
            <el-option v-for="agent in agents" :key="agent.id" :label="agent.agent_name" :value="agent.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('common.environment')">
          <el-select v-model="form.env_id" :placeholder="t('env.placeholder')">
            <el-option v-for="env in environments" :key="env.id" :label="env.env_name" :value="env.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="Case IDs">
          <el-input v-model="caseIdsInput" :placeholder="t('testCase.tagsPlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('task.judgeModel')">
          <el-input v-model="form.judge_llm_model" placeholder="Optional: gpt-4" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="submitForm">{{ t('common.add') }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="resultsDialogVisible" :title="t('task.viewDetail')" width="95%">
      <div v-if="selectedTask">
        <div class="task-summary">
          <el-tag type="success">{{ t('common.success') }}: {{ selectedTask.stats_json?.passed || 0 }}</el-tag>
          <el-tag type="danger">{{ t('common.failed') }}: {{ selectedTask.stats_json?.failed || 0 }}</el-tag>
          <el-tag type="info">Total: {{ selectedTask.stats_json?.total || 0 }}</el-tag>
        </div>
        <el-table :data="results" max-height="400" @row-click="handleRowClick" highlight-current-row>
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="case_id" label="Case ID" width="100" />
          <el-table-column prop="agent_sql" :label="t('task.agentSql')" show-overflow-tooltip />
          <el-table-column prop="execution_status" :label="t('task.status')" width="120">
            <template #default="{ row }">
              <el-tag :type="row.data_diff_passed ? 'success' : 'danger'">
                {{ row.execution_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="t('task.dataDiff')" width="100">
            <template #default="{ row }">
              <el-tag :type="row.data_diff_passed ? 'success' : 'danger'">
                {{ row.data_diff_passed ? 'PASS' : 'FAIL' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="t('task.actions')" width="150">
            <template #default="{ row }">
              <el-button size="small" @click.stop="viewDiagnosis(row)">{{ t('task.diagnosis') }}</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div v-if="currentResult" class="detail-comparison-area">
          <el-divider>{{ t('task.sqlDiff') }}</el-divider>
          <el-row :gutter="20">
            <el-col :span="12">
              <div class="sql-box">
                <div class="sql-box-header">{{ t('task.goldenSql') }}</div>
                <pre class="sql-content">{{ getGoldenSql(currentResult.case_id) }}</pre>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="sql-box">
                <div class="sql-box-header">{{ t('task.agentSql') }}</div>
                <pre class="sql-content" :class="{ 'error-sql': !currentResult.data_diff_passed }">{{ currentResult.agent_sql }}</pre>
              </div>
            </el-col>
          </el-row>

          <el-divider>{{ t('task.dataDiff') }}</el-divider>
          <el-row :gutter="20">
            <el-col :span="12">
              <div class="data-box">
                <div class="data-box-header">{{ t('task.goldenData') }}</div>
                <el-table :data="currentResult.golden_data?.slice(0, 10)" size="small" border>
                  <el-table-column v-for="col in getDataColumns(currentResult.golden_data)" :key="col" :prop="col" :label="col" />
                </el-table>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="data-box">
                <div class="data-box-header">{{ t('task.agentData') }}</div>
                <el-table :data="currentResult.agent_data?.slice(0, 10)" size="small" border>
                  <el-table-column v-for="col in getDataColumns(currentResult.agent_data)" :key="col" :prop="col" :label="col" />
                </el-table>
              </div>
            </el-col>
          </el-row>
        </div>
      </div>
    </el-dialog>

    <el-dialog v-model="diagnosisDialogVisible" :title="t('task.diagnosis')" width="600px">
      <pre class="diagnosis-content">{{ diagnosis }}</pre>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getTasks, createTask, deleteTask, startTask as apiStartTask, getResults, getDiagnosis, getAgents, getSchemaEnvs } from '../api'
import type { EvaluationTask, EvaluationResult, AgentConfig, SchemaEnv } from '../types'
import { t } from '../i18n'

const tasks = ref<EvaluationTask[]>([])
const results = ref<EvaluationResult[]>([])
const agents = ref<AgentConfig[]>([])
const environments = ref<SchemaEnv[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const resultsDialogVisible = ref(false)
const diagnosisDialogVisible = ref(false)
const selectedTask = ref<EvaluationTask | null>(null)
const currentResult = ref<EvaluationResult | null>(null)
const testCases = ref<Record<number, string>>({})
const diagnosis = ref('')
const caseIdsInput = ref('')

const form = ref({
  task_name: '',
  agent_id: undefined as number | undefined,
  env_id: undefined as number | undefined,
  judge_llm_model: '',
})

const loadTasks = async () => {
  loading.value = true
  try {
    const res = await getTasks()
    tasks.value = res.data
  } catch (error) {
    ElMessage.error(t('common.failed'))
  } finally {
    loading.value = false
  }
}

const loadAgents = async () => {
  const res = await getAgents()
  agents.value = res.data
}

const loadEnvironments = async () => {
  const res = await getSchemaEnvs()
  environments.value = res.data
}

const showCreateDialog = () => {
  form.value = { task_name: '', agent_id: undefined, env_id: undefined, judge_llm_model: '' }
  caseIdsInput.value = ''
  dialogVisible.value = true
}

const submitForm = async () => {
  const data: any = { ...form.value }
  if (caseIdsInput.value) {
    data.case_ids = caseIdsInput.value.split(',').map(s => parseInt(s.trim())).filter(n => !isNaN(n))
  }
  try {
    await createTask(data)
    ElMessage.success(t('task.createSuccess'))
    dialogVisible.value = false
    loadTasks()
  } catch (error) {
    ElMessage.error(t('common.failed'))
  }
}

const deleteTaskById = async (id: number) => {
  try {
    await deleteTask(id)
    ElMessage.success(t('common.success'))
    loadTasks()
  } catch (error) {
    ElMessage.error(t('common.failed'))
  }
}

const startTask = async (id: number) => {
  try {
    await apiStartTask(id)
    ElMessage.success(t('common.success'))
    loadTasks()
  } catch (error) {
    ElMessage.error(t('common.failed'))
  }
}

const viewResults = async (task: EvaluationTask) => {
  selectedTask.value = task
  currentResult.value = null
  try {
    const res = await getResults(task.id)
    results.value = res.data
    resultsDialogVisible.value = true
    
    // Also load golden SQLs for comparison
    const casesRes = await api.get('/test-cases', { params: { env_id: task.env_id } })
    testCases.value = casesRes.data.reduce((acc: any, c: any) => {
      acc[c.id] = c.golden_sql
      return acc
    }, {})
  } catch (error) {
    ElMessage.error(t('common.failed'))
  }
}

const handleRowClick = (row: EvaluationResult) => {
  currentResult.value = row
}

const getGoldenSql = (caseId: number) => {
  return testCases.value[caseId] || 'Loading...'
}

const getDataColumns = (data: any[]) => {
  if (!data || data.length === 0) return []
  return Object.keys(data[0])
}

const viewDiagnosis = async (result: EvaluationResult) => {
  try {
    const res = await getDiagnosis(result.id)
    diagnosis.value = res.data.diagnosis || 'No diagnosis available'
    diagnosisDialogVisible.value = true
  } catch (error) {
    ElMessage.error(t('common.failed'))
  }
}

const getStatusType = (status: string) => {
  const types: Record<string, string> = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger',
  }
  return types[status] || 'info'
}

const formatDate = (date: string) => {
  return new Date(date).toLocaleString()
}

onMounted(() => {
  loadTasks()
  loadAgents()
  loadEnvironments()
})
</script>

<style scoped>
.task-execution {
  /* padding: 20px; 已被 App.vue 统一管理 */
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.task-summary {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.diagnosis-content {
  background: #f5f5f5;
  padding: 15px;
  border-radius: 4px;
  white-space: pre-wrap;
  font-family: monospace;
  max-height: 400px;
  overflow-y: auto;
}

.detail-comparison-area {
  margin-top: 20px;
  padding: 20px;
  background: #fafafa;
  border: 1px solid #ebeef5;
  border-radius: 8px;
}

.sql-box, .data-box {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  overflow: hidden;
}

.sql-box-header, .data-box-header {
  background: #f0f2f5;
  padding: 8px 12px;
  font-weight: bold;
  border-bottom: 1px solid #dcdfe6;
}

.sql-content {
  padding: 12px;
  background: #fff;
  margin: 0;
  min-height: 100px;
  font-family: 'Courier New', Courier, monospace;
  font-size: 13px;
}

.error-sql {
  background: #fff0f0;
}
</style>
