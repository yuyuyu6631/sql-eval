<template>
  <div class="ai-design-page">
    <section class="hero-card m-card">
      <div class="hero-copy">
        <p class="hero-kicker">AI设计工作区</p>
        <h1 class="page-heading">AI测试设计工作台</h1>
        <p class="page-subtitle">通过四步菜单完成知识录入、设计分析、测试点筛选和用例生成。</p>
      </div>
      <div class="hero-actions">
        <button class="m-btn secondary" @click="refreshCurrentStep">刷新当前步骤</button>
        <button class="m-btn primary" @click="goStep(nextAvailableStep)">继续推进</button>
      </div>
    </section>

    <section class="step-nav m-card" aria-label="AI设计步骤导航">
      <button
        v-for="(step, index) in stepItems"
        :key="step.key"
        class="step-tab"
        :class="{ 'is-active': activeStep === step.key, 'is-complete': step.status === 'done', 'is-blocked': !step.enabled }"
        :disabled="!step.enabled"
        @click="goStep(step.key)"
      >
        <span class="step-tab-index">0{{ index + 1 }}</span>
        <span class="step-tab-main">
          <span class="step-tab-code">{{ step.code }}</span>
          <span class="step-tab-name">{{ step.label }}</span>
        </span>
        <span class="step-tab-status">{{ step.statusText }}</span>
      </button>
    </section>

    <section class="coord-grid">
      <article class="status-card m-card">
        <span class="status-label">当前知识</span>
        <strong class="status-value">{{ currentKnowledgeTitle }}</strong>
        <span class="status-note">知识来源 / KNS</span>
      </article>
      <article class="status-card m-card">
        <span class="status-label">设计记录</span>
        <strong class="status-value">{{ currentDesignId ? `#${currentDesignId}` : '-' }}</strong>
        <span class="status-note">设计摘要 / DSN</span>
      </article>
      <article class="status-card m-card">
        <span class="status-label">已选测试点</span>
        <strong class="status-value">{{ selectedPointCount }}</strong>
        <span class="status-note">测试点范围 / PTS</span>
      </article>
      <article class="status-card m-card">
        <span class="status-label">已生成用例</span>
        <strong class="status-value">{{ cases.length }}</strong>
        <span class="status-note">用例产出 / CAS</span>
      </article>
    </section>

    <section class="trace-strip m-card">
      <div class="trace-item">
        <span class="trace-label">模型</span>
        <span class="trace-value">{{ currentModelLabel }}</span>
      </div>
      <div class="trace-item">
        <span class="trace-label">最近来源</span>
        <span class="trace-value">{{ latestTrace.source || '-' }}</span>
      </div>
      <div class="trace-item">
        <span class="trace-label">回退原因</span>
        <span class="trace-value">{{ latestTrace.fallback_reason || '无' }}</span>
      </div>
      <div class="trace-item">
        <span class="trace-label">设计模式</span>
        <span class="trace-value">{{ outputForm.generate_mode }}</span>
      </div>
    </section>

    <section v-if="activeStep === 'kns'" class="panel-grid">
      <article class="m-card panel-card">
        <div class="panel-head">
          <div>
            <p class="panel-code">KNS</p>
            <h2 class="panel-title">知识输入</h2>
          </div>
          <p class="panel-desc">录入需求、规则、接口说明或上传已有材料。</p>
        </div>
        <div class="form-grid">
          <el-input v-model="knowledgeForm.title" placeholder="需求标题，例如：登录风控能力升级" />
          <el-input v-model="knowledgeForm.module_name" placeholder="所属模块，例如：登录 / 支付 / 订单" />
          <el-input v-model="knowledgeForm.content" type="textarea" :rows="8" placeholder="输入需求说明、业务规则、接口文档、异常处理逻辑等内容" />
          <el-input v-model="knowledgeForm.extra_instruction" type="textarea" :rows="4" placeholder="补充本轮重点，例如：优先覆盖异常流、边界值、权限校验" />
        </div>
        <div class="actions-row">
          <button class="m-btn secondary" @click="loadKnowledge">刷新列表</button>
          <button class="m-btn secondary" @click="triggerImport">导入文件</button>
          <button class="m-btn primary" @click="saveKnowledge">保存并进入 DSN</button>
          <input ref="fileInputRef" type="file" style="display: none" accept=".txt,.md,.json,.csv" @change="onImportFileChange" />
        </div>
      </article>

      <article class="m-card panel-card">
        <div class="panel-head">
          <div>
            <p class="panel-code">知识库</p>
            <h2 class="panel-title">历史知识</h2>
          </div>
          <p class="panel-desc">可以直接复用已有知识源继续设计。</p>
        </div>
        <el-table :data="knowledgeList" size="small" empty-text="暂无知识记录">
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column prop="title" label="标题" min-width="180" />
          <el-table-column prop="module_name" label="模块" width="120" />
          <el-table-column prop="source_type" label="来源" width="120" />
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <button class="m-btn sm secondary" @click="useKnowledge(row)">使用</button>
            </template>
          </el-table-column>
        </el-table>
      </article>
    </section>

    <section v-else-if="activeStep === 'dsn'" class="panel-grid">
      <article class="m-card panel-card">
        <div class="panel-head">
          <div>
            <p class="panel-code">DSN</p>
            <h2 class="panel-title">设计分析</h2>
          </div>
          <p class="panel-desc">把知识转成可执行的测试设计摘要，并沉淀可追踪信息。</p>
        </div>
        <div class="form-grid compact-grid">
          <el-select v-model="outputForm.model_name" placeholder="选择设计模型">
            <el-option v-for="cfg in designConfigs" :key="cfg.id" :label="`${cfg.name} (${cfg.model_name})`" :value="cfg.model_name" />
          </el-select>
          <el-select v-model="outputForm.generate_mode">
            <el-option label="simple" value="simple" />
            <el-option label="standard" value="standard" />
            <el-option label="deep" value="deep" />
          </el-select>
        </div>
        <div class="actions-row">
          <button class="m-btn secondary" @click="goStep('kns')">返回 KNS</button>
          <button class="m-btn primary" @click="generateSummary">生成设计摘要</button>
          <button class="m-btn secondary" :disabled="!currentDesignId" @click="goStep('pts')">前往 PTS</button>
        </div>
        <div class="summary-card">
          <div class="summary-block"><span class="summary-label">功能范围</span><p>{{ renderList(summary.function_scope) }}</p></div>
          <div class="summary-block"><span class="summary-label">覆盖维度</span><p>{{ renderList(summary.coverage_dimensions) }}</p></div>
          <div class="summary-block"><span class="summary-label">风险点</span><p>{{ renderList(summary.risks) }}</p></div>
          <div class="summary-block"><span class="summary-label">缺失信息</span><p>{{ renderList(summary.missing_info) }}</p></div>
        </div>
      </article>

      <article class="m-card panel-card side-panel">
        <div class="panel-head">
          <div>
            <p class="panel-code">链路信息</p>
            <h2 class="panel-title">本步链路</h2>
          </div>
          <p class="panel-desc">查看最近一次设计生成来源和模型信息。</p>
        </div>
        <div class="trace-card">
          <div>来源: <span class="font-mono">{{ designTrace.source || '-' }}</span></div>
          <div>回退原因: <span class="font-mono">{{ designTrace.fallback_reason || '无' }}</span></div>
          <div>模型名称: <span class="font-mono">{{ designTrace.model_name || '-' }}</span></div>
        </div>
        <div class="raw-output-card">
          <div class="summary-label">输出预览</div>
          <p>{{ designTrace.model_raw_output || '暂无输出预览' }}</p>
        </div>
      </article>
    </section>

    <section v-else-if="activeStep === 'pts'" class="panel-grid">
      <article class="m-card panel-card">
        <div class="panel-head">
          <div>
            <p class="panel-code">PTS</p>
            <h2 class="panel-title">测试点管理</h2>
          </div>
          <p class="panel-desc">按分类和优先级筛选测试点，控制哪些点进入用例生成。</p>
        </div>
        <div class="actions-row">
          <button class="m-btn secondary" @click="goStep('dsn')">返回 DSN</button>
          <button class="m-btn primary" @click="generatePoints">重新生成测试点</button>
          <button class="m-btn secondary" :disabled="selectedPointCount === 0" @click="goStep('cas')">前往 CAS</button>
        </div>
        <el-table :data="points" size="small" empty-text="暂无测试点，请先生成">
          <el-table-column label="选中" width="72">
            <template #default="{ row }">
              <el-checkbox v-model="row.selected" @change="updatePointSelection(row)" />
            </template>
          </el-table-column>
          <el-table-column prop="category" label="分类" width="140" />
          <el-table-column prop="content" label="内容" min-width="260" />
          <el-table-column prop="priority" label="优先级" width="100" />
        </el-table>
      </article>

      <article class="m-card panel-card side-panel">
        <div class="panel-head">
          <div>
            <p class="panel-code">测试点统计</p>
            <h2 class="panel-title">选择概览</h2>
          </div>
          <p class="panel-desc">确认进入用例生成的测试点范围。</p>
        </div>
        <div class="metric-stack">
          <div class="mini-metric"><span>总测试点</span><strong>{{ points.length }}</strong></div>
          <div class="mini-metric"><span>已选测试点</span><strong>{{ selectedPointCount }}</strong></div>
          <div class="mini-metric"><span>P0 / P1</span><strong>{{ highPriorityPointCount }}</strong></div>
        </div>
        <div class="trace-card">
          <div>来源: <span class="font-mono">{{ pointTrace.source || '-' }}</span></div>
          <div>回退原因: <span class="font-mono">{{ pointTrace.fallback_reason || '无' }}</span></div>
          <div>模型名称: <span class="font-mono">{{ pointTrace.model_name || '-' }}</span></div>
        </div>
      </article>
    </section>

    <section v-else class="panel-grid">
      <article class="m-card panel-card">
        <div class="panel-head">
          <div>
            <p class="panel-code">CAS</p>
            <h2 class="panel-title">测试用例生成</h2>
          </div>
          <p class="panel-desc">基于已选测试点生成、编辑并导出测试用例。</p>
        </div>
        <div class="form-grid compact-grid">
          <el-select v-model="outputForm.case_type">
            <el-option label="functional" value="functional" />
            <el-option label="api" value="api" />
            <el-option label="ui" value="ui" />
            <el-option label="generic" value="generic" />
          </el-select>
          <el-input-number v-model="outputForm.output_count" :min="1" :max="50" />
        </div>
        <div class="actions-row wrap">
          <button class="m-btn secondary" @click="goStep('pts')">返回 PTS</button>
          <button class="m-btn primary" @click="generateCases">生成测试用例</button>
          <button class="m-btn secondary" @click="loadCases">刷新列表</button>
          <button class="m-btn secondary" @click="doExport('markdown')">导出 Markdown 文档</button>
          <button class="m-btn secondary" @click="doExport('json')">导出 JSON 数据</button>
          <button class="m-btn secondary" @click="doExport('csv')">导出 CSV 数据</button>
          <button class="m-btn secondary" @click="doExport('xlsx')">导出 Excel 文件</button>
        </div>
        <el-table :data="cases" size="small" empty-text="暂无测试用例，请先生成">
          <el-table-column prop="title" label="标题" min-width="240" />
          <el-table-column prop="case_type" label="类型" width="110" />
          <el-table-column prop="priority" label="优先级" width="90" />
          <el-table-column prop="status" label="状态" width="120" />
          <el-table-column label="操作" width="200">
            <template #default="{ row }">
              <div class="actions">
                <button class="m-btn sm secondary" @click="openCaseEditor(row)">编辑</button>
                <button class="m-btn sm secondary" @click="markCase(row, 'confirmed')">确认</button>
                <button class="m-btn sm danger" @click="removeCase(row.id)">删除</button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </article>

      <article class="m-card panel-card side-panel">
        <div class="panel-head">
          <div>
            <p class="panel-code">生成信息</p>
            <h2 class="panel-title">生成链路</h2>
          </div>
          <p class="panel-desc">导出前先确认模型、来源和生成模式。</p>
        </div>
        <div class="trace-card">
          <div>来源: <span class="font-mono">{{ caseTrace.source || '-' }}</span></div>
          <div>回退原因: <span class="font-mono">{{ caseTrace.fallback_reason || '无' }}</span></div>
          <div>模型名称: <span class="font-mono">{{ caseTrace.model_name || '-' }}</span></div>
        </div>
        <div class="raw-output-card">
          <div class="summary-label">输出预览</div>
          <p>{{ caseTrace.model_raw_output || '暂无输出预览' }}</p>
        </div>
      </article>
    </section>

    <el-dialog v-model="caseDialogVisible" title="编辑测试用例" width="680px">
      <el-form :model="caseForm" label-width="100px">
        <el-form-item label="标题"><el-input v-model="caseForm.title" /></el-form-item>
        <el-form-item label="前置条件"><el-input v-model="caseForm.precondition" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="步骤"><el-input v-model="stepsText" type="textarea" :rows="5" placeholder="每行填写一个测试步骤" /></el-form-item>
        <el-form-item label="预期结果"><el-input v-model="caseForm.expected_result" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="caseForm.priority" style="width: 100%">
            <el-option label="P0" value="P0" />
            <el-option label="P1" value="P1" />
            <el-option label="P2" value="P2" />
            <el-option label="P3" value="P3" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="caseForm.status" style="width: 100%">
            <el-option label="new" value="new" />
            <el-option label="confirmed" value="confirmed" />
            <el-option label="optimize_needed" value="optimize_needed" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <button class="m-btn secondary" @click="caseDialogVisible = false">取消</button>
        <button class="m-btn primary" @click="saveCaseEdit">保存</button>
      </template>
    </el-dialog>

    <el-dialog v-model="deleteDialogVisible" title="确认删除" width="420px">
      <p>确认删除该测试用例？此操作不可撤销。</p>
      <template #footer>
        <button class="m-btn secondary" @click="deleteDialogVisible = false">取消</button>
        <button class="m-btn danger" @click="confirmDeleteCase">删除</button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { AITestCase, AITestPoint, DesignSummary, KnowledgeSource, ModelConfig } from '../types'
import {
  createKnowledge,
  deleteDesignCase,
  exportDesignCases,
  generateDesign,
  generateDesignCases,
  generateDesignPoints,
  getModelConfigs,
  importKnowledgeFile,
  listDesignCases,
  listDesignPoints,
  listKnowledge,
  updateDesignCase,
  updateDesignPoint,
} from '../api'

type StepKey = 'kns' | 'dsn' | 'pts' | 'cas'

const route = useRoute()
const router = useRouter()

const knowledgeForm = reactive({ title: '', module_name: '', content: '', extra_instruction: '' })
const outputForm = reactive({
  model_name: '',
  generate_mode: 'standard' as 'simple' | 'standard' | 'deep',
  case_type: 'functional' as 'functional' | 'api' | 'ui' | 'generic',
  output_count: 20,
})

const knowledgeList = ref<KnowledgeSource[]>([])
const designConfigs = ref<ModelConfig[]>([])
const summary = ref<DesignSummary>({ function_scope: [], coverage_dimensions: [], risks: [], missing_info: [] })
const points = ref<AITestPoint[]>([])
const cases = ref<AITestCase[]>([])
const designTrace = ref<Record<string, any>>({})
const pointTrace = ref<Record<string, any>>({})
const caseTrace = ref<Record<string, any>>({})
const currentKnowledgeId = ref<number | null>(null)
const currentDesignId = ref<number | null>(null)
const caseDialogVisible = ref(false)
const deleteDialogVisible = ref(false)
const deletingCaseId = ref<number | null>(null)
const caseForm = ref<Partial<AITestCase>>({})
const stepsText = ref('')
const fileInputRef = ref<HTMLInputElement | null>(null)

const normalizeStep = (value: unknown): StepKey => (value === 'kns' || value === 'dsn' || value === 'pts' || value === 'cas' ? value : 'kns')
const activeStep = computed<StepKey>(() => normalizeStep(route.query.step))
const selectedPointCount = computed(() => points.value.filter((item) => item.selected).length)
const highPriorityPointCount = computed(() => points.value.filter((item) => item.priority === 'P0' || item.priority === 'P1').length)
const currentKnowledgeTitle = computed(() => knowledgeList.value.find((item) => item.id === currentKnowledgeId.value)?.title || knowledgeForm.title || '-')
const currentModelLabel = computed(() => outputForm.model_name || '未选择')
const latestTrace = computed(() => (caseTrace.value.source ? caseTrace.value : pointTrace.value.source ? pointTrace.value : designTrace.value))

const stepItems = computed(() => {
  const hasKnowledge = Boolean(currentKnowledgeId.value)
  const hasDesign = Boolean(currentDesignId.value)
  const hasPoints = points.value.length > 0
  const hasCases = cases.value.length > 0
  return [
    { key: 'kns' as StepKey, code: 'KNS', label: '知识输入', enabled: true, status: hasKnowledge ? 'done' : 'active', statusText: hasKnowledge ? '已保存' : '待录入' },
    { key: 'dsn' as StepKey, code: 'DSN', label: '设计分析', enabled: hasKnowledge, status: hasDesign ? 'done' : hasKnowledge ? 'active' : 'locked', statusText: hasDesign ? '已生成' : hasKnowledge ? '待分析' : '未解锁' },
    { key: 'pts' as StepKey, code: 'PTS', label: '测试点', enabled: hasDesign, status: hasPoints ? 'done' : hasDesign ? 'active' : 'locked', statusText: hasPoints ? '可筛选' : hasDesign ? '待生成' : '未解锁' },
    { key: 'cas' as StepKey, code: 'CAS', label: '测试用例', enabled: hasDesign && selectedPointCount.value > 0, status: hasCases ? 'done' : hasDesign && selectedPointCount.value > 0 ? 'active' : 'locked', statusText: hasCases ? '已产出' : hasDesign && selectedPointCount.value > 0 ? '待生成' : '未解锁' },
  ]
})

const nextAvailableStep = computed<StepKey>(() => {
  if (!currentKnowledgeId.value) return 'kns'
  if (!currentDesignId.value) return 'dsn'
  if (points.value.length === 0 || selectedPointCount.value === 0) return 'pts'
  return 'cas'
})

const renderList = (items?: string[]) => (items && items.length > 0 ? items.join('、') : '-')
const goStep = async (step: StepKey) => router.replace({ query: { ...route.query, step } })
const triggerImport = () => fileInputRef.value?.click()

const resetDesignStage = () => {
  currentDesignId.value = null
  summary.value = { function_scope: [], coverage_dimensions: [], risks: [], missing_info: [] }
  designTrace.value = {}
  resetPointStage()
}

const resetPointStage = () => {
  points.value = []
  pointTrace.value = {}
  resetCaseStage()
}

const resetCaseStage = () => {
  cases.value = []
  caseTrace.value = {}
}

const onImportFileChange = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  try {
    const response = await importKnowledgeFile(file, {
      title: knowledgeForm.title || undefined,
      module_name: knowledgeForm.module_name || undefined,
      extra_instruction: knowledgeForm.extra_instruction || undefined,
    })
    resetDesignStage()
    currentKnowledgeId.value = response.data.id
    ElMessage.success(`导入成功: ${response.data.filename}`)
    await loadKnowledge()
    await goStep('dsn')
  } catch {
    ElMessage.error('文件导入失败')
  } finally {
    input.value = ''
  }
}

const loadKnowledge = async () => {
  const response = await listKnowledge()
  knowledgeList.value = response.data
}

const loadDesignConfigs = async () => {
  const response = await getModelConfigs('design')
  designConfigs.value = response.data.filter((item) => item.enabled)
  if (!outputForm.model_name && designConfigs.value.length > 0) outputForm.model_name = designConfigs.value[0].model_name
}

const loadPoints = async () => {
  if (!currentDesignId.value) return
  const response = await listDesignPoints(currentDesignId.value)
  points.value = response.data
}

const loadCases = async () => {
  if (!currentDesignId.value) return
  const response = await listDesignCases(currentDesignId.value)
  cases.value = response.data
}

const saveKnowledge = async () => {
  if (!knowledgeForm.title || !knowledgeForm.content) {
    ElMessage.warning('请填写标题和知识内容')
    return
  }
  try {
    const response = await createKnowledge({
      title: knowledgeForm.title,
      module_name: knowledgeForm.module_name,
      content: knowledgeForm.content,
      extra_instruction: knowledgeForm.extra_instruction,
      source_type: 'manual',
    })
    resetDesignStage()
    currentKnowledgeId.value = response.data.id
    ElMessage.success('知识已保存')
    await loadKnowledge()
    await goStep('dsn')
  } catch {
    ElMessage.error('知识保存失败')
  }
}

const useKnowledge = async (row: KnowledgeSource) => {
  resetDesignStage()
  currentKnowledgeId.value = row.id
  knowledgeForm.title = row.title
  knowledgeForm.module_name = row.module_name || ''
  knowledgeForm.content = row.content
  knowledgeForm.extra_instruction = row.extra_instruction || ''
  await goStep('dsn')
}

const generateSummary = async () => {
  if (!currentKnowledgeId.value) {
    ElMessage.warning('请先在 KNS 中保存或选择知识')
    return
  }
  try {
    const response = await generateDesign({
      knowledge_id: currentKnowledgeId.value,
      model_name: outputForm.model_name || undefined,
      design_mode: outputForm.generate_mode,
    })
    currentDesignId.value = response.data.design_id
    summary.value = response.data.summary
    designTrace.value = { source: response.data.source, fallback_reason: response.data.fallback_reason, model_name: response.data.model_name, model_raw_output: response.data.model_raw_output }
    resetPointStage()
    ElMessage.success('设计摘要已生成')
    await goStep('pts')
  } catch {
    ElMessage.error('生成设计摘要失败')
  }
}

const generatePoints = async () => {
  if (!currentDesignId.value) {
    ElMessage.warning('请先生成设计摘要')
    return
  }
  try {
    const response = await generateDesignPoints({ design_id: currentDesignId.value, model_name: outputForm.model_name || undefined })
    points.value = response.data.points
    pointTrace.value = { source: (response.data as any).source, fallback_reason: (response.data as any).fallback_reason, model_name: (response.data as any).model_name, model_raw_output: (response.data as any).model_raw_output }
    resetCaseStage()
    ElMessage.success('测试点已生成')
    await goStep('cas')
  } catch {
    ElMessage.error('生成测试点失败')
  }
}

const updatePointSelection = async (row: AITestPoint) => {
  try {
    await updateDesignPoint(row.id, { selected: row.selected })
  } catch {
    ElMessage.error('更新测试点失败')
  }
}

const generateCases = async () => {
  if (!currentDesignId.value) {
    ElMessage.warning('请先完成设计分析')
    return
  }
  const selectedIds = points.value.filter((point) => point.selected).map((point) => point.id)
  if (selectedIds.length === 0) {
    ElMessage.warning('请至少选择一个测试点')
    return
  }
  try {
    const response = await generateDesignCases({
      design_id: currentDesignId.value,
      point_ids: selectedIds,
      model_name: outputForm.model_name || undefined,
      case_type: outputForm.case_type,
      generate_mode: outputForm.generate_mode,
      output_count: outputForm.output_count,
    })
    caseTrace.value = { source: (response.data as any).source, fallback_reason: (response.data as any).fallback_reason, model_name: (response.data as any).model_name, model_raw_output: (response.data as any).model_raw_output }
    ElMessage.success('测试用例已生成')
    await loadCases()
  } catch {
    ElMessage.error('生成测试用例失败')
  }
}

const markCase = async (row: AITestCase, status: 'confirmed' | 'optimize_needed') => {
  await updateDesignCase(row.id, { status })
  await loadCases()
}

const removeCase = async (id: number) => {
  deletingCaseId.value = id
  deleteDialogVisible.value = true
}

const confirmDeleteCase = async () => {
  if (!deletingCaseId.value) return
  await deleteDesignCase(deletingCaseId.value)
  deleteDialogVisible.value = false
  deletingCaseId.value = null
  await loadCases()
}

const openCaseEditor = (row: AITestCase) => {
  caseForm.value = { ...row }
  stepsText.value = (row.steps || []).join('\n')
  caseDialogVisible.value = true
}

const saveCaseEdit = async () => {
  if (!caseForm.value.id) return
  const steps = stepsText.value.split('\n').map((item) => item.trim()).filter(Boolean)
  await updateDesignCase(caseForm.value.id, {
    title: caseForm.value.title,
    precondition: caseForm.value.precondition,
    expected_result: caseForm.value.expected_result,
    steps,
    priority: caseForm.value.priority,
    status: caseForm.value.status,
  })
  caseDialogVisible.value = false
  await loadCases()
}

const doExport = async (format: 'markdown' | 'json' | 'csv' | 'xlsx') => {
  if (!currentDesignId.value) {
    ElMessage.warning('没有可导出的设计数据')
    return
  }
  const response = await exportDesignCases(currentDesignId.value, format)
  const mimeMap: Record<string, string> = {
    markdown: 'text/markdown;charset=utf-8',
    json: 'application/json;charset=utf-8',
    csv: 'text/csv;charset=utf-8',
    xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  }
  const blob = new Blob([response.data], { type: mimeMap[format] || 'application/octet-stream' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `ai-test-design-${currentDesignId.value}.${format === 'markdown' ? 'md' : format}`
  anchor.click()
  URL.revokeObjectURL(url)
}

const refreshCurrentStep = async () => {
  if (activeStep.value === 'kns') return loadKnowledge()
  if (activeStep.value === 'dsn') return loadDesignConfigs()
  if (activeStep.value === 'pts') return loadPoints()
  return loadCases()
}

watch(
  () => route.query.step,
  async (value) => {
    const step = normalizeStep(value)
    if (step === 'pts' && currentDesignId.value) await loadPoints()
    if (step === 'cas' && currentDesignId.value) await loadCases()
  },
  { immediate: true },
)

onMounted(async () => {
  if (!route.query.step) await goStep('kns')
  await Promise.all([loadKnowledge(), loadDesignConfigs()])
})
</script>

<style scoped>
.ai-design-page { display: flex; flex-direction: column; gap: 16px; }
.hero-card { display: flex; justify-content: space-between; gap: 20px; padding: 24px; background: radial-gradient(circle at top left, rgba(59, 130, 246, 0.12), transparent 38%), radial-gradient(circle at bottom right, rgba(16, 185, 129, 0.12), transparent 32%), linear-gradient(135deg, var(--m-surface), var(--m-surface-bright)); }
.hero-copy { display: flex; flex-direction: column; gap: 8px; }
.hero-kicker, .panel-code { margin: 0; font-size: 12px; letter-spacing: 0.16em; text-transform: uppercase; color: var(--m-primary); font-weight: 700; }
.page-heading { margin: 0; font-size: 28px; line-height: 1.2; color: var(--m-text); }
.page-subtitle { margin: 0; max-width: 620px; font-size: 14px; color: var(--m-text-muted); }
.hero-actions { display: flex; gap: 12px; align-items: flex-start; flex-wrap: wrap; }
.step-nav { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; padding: 14px; }
.step-tab { border: 1px solid var(--m-border); background: var(--m-surface-bright); border-radius: var(--radius-lg); padding: 14px; display: flex; flex-direction: column; gap: 8px; text-align: left; transition: border-color var(--t-normal), transform var(--t-normal), box-shadow var(--t-normal); }
.step-tab:hover:not(:disabled) { transform: translateY(-1px); border-color: var(--m-primary); }
.step-tab.is-active { border-color: var(--m-primary); box-shadow: 0 14px 28px rgba(59, 130, 246, 0.12); }
.step-tab.is-complete .step-tab-code { color: var(--m-success, #0f9f6e); }
.step-tab.is-blocked { opacity: 0.56; cursor: not-allowed; }
.step-tab-index { font-size: 11px; letter-spacing: 0.08em; color: var(--m-text-muted); }
.step-tab-main { display: flex; align-items: baseline; gap: 10px; }
.step-tab-code { font-size: 18px; font-weight: 800; color: var(--m-text); }
.step-tab-name { font-size: 14px; font-weight: 600; color: var(--m-text); }
.step-tab-status { font-size: 12px; color: var(--m-text-muted); }
.coord-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.status-card { display: flex; flex-direction: column; gap: 8px; padding: 18px; }
.status-label, .trace-label, .summary-label { font-size: 12px; color: var(--m-text-muted); text-transform: uppercase; letter-spacing: 0.08em; }
.status-value { font-size: 22px; color: var(--m-text); line-height: 1.2; }
.status-note { font-size: 12px; color: var(--m-text-muted); }
.trace-strip { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; padding: 16px; }
.trace-item { display: flex; flex-direction: column; gap: 6px; }
.trace-value { color: var(--m-text); font-size: 14px; word-break: break-word; }
.panel-grid { display: grid; grid-template-columns: minmax(0, 1.7fr) minmax(300px, 0.9fr); gap: 16px; }
.panel-card { padding: 20px; display: flex; flex-direction: column; gap: 16px; }
.panel-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.panel-title { margin: 4px 0 0; font-size: 22px; color: var(--m-text); }
.panel-desc { margin: 0; max-width: 320px; font-size: 13px; line-height: 1.6; color: var(--m-text-muted); }
.form-grid { display: grid; gap: 12px; }
.compact-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.actions-row { display: flex; gap: 10px; align-items: center; }
.actions-row.wrap { flex-wrap: wrap; }
.actions { display: flex; gap: 8px; }
.summary-card, .trace-card, .raw-output-card, .metric-stack { border: 1px solid var(--m-border); border-radius: var(--radius-lg); background: var(--m-surface-bright); padding: 16px; }
.summary-card { display: grid; gap: 14px; }
.summary-block p, .raw-output-card p { margin: 6px 0 0; color: var(--m-text); line-height: 1.7; white-space: pre-wrap; word-break: break-word; }
.trace-card { display: grid; gap: 8px; font-size: 13px; color: var(--m-text); }
.font-mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
.metric-stack { display: grid; gap: 10px; }
.mini-metric { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--m-border); padding-bottom: 10px; }
.mini-metric:last-child { border-bottom: none; padding-bottom: 0; }
.mini-metric span { color: var(--m-text-muted); font-size: 13px; }
.mini-metric strong { color: var(--m-text); font-size: 18px; }
@media (max-width: 1200px) {
  .coord-grid, .trace-strip, .step-nav { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .panel-grid { grid-template-columns: 1fr; }
}
@media (max-width: 768px) {
  .hero-card, .panel-head { flex-direction: column; }
  .step-nav, .coord-grid, .trace-strip, .compact-grid { grid-template-columns: 1fr; }
  .actions-row { flex-wrap: wrap; }
}
</style>
