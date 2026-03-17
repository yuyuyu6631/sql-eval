<template>
  <div class="testcase-page">
    <div class="page-toolbar">
      <h1 class="page-heading">{{ t('testCase.title') }}</h1>
      <div class="toolbar-right">
        <!-- 环境筛选 -->
        <el-select
          v-model="filterEnvId"
          :placeholder="t('testCase.filterByEnv')"
          clearable
          style="width: 180px"
          @change="loadCases"
        >
          <el-option v-for="env in environments" :key="env.id" :label="env.env_name" :value="env.id" />
        </el-select>
        <button class="m-btn secondary" @click="showBatchCreate" aria-label="批量导入测试用例">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
          {{ t('testCase.batchImport') }}
        </button>
        <button class="m-btn primary" @click="showCreateDialog" aria-label="新建测试用例">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          {{ t('common.add') }}
        </button>
      </div>
    </div>

    <!-- 用例表格 -->
    <div class="m-card table-card">
      <div v-if="isLoading">
        <div v-for="i in 5" :key="i" class="m-skeleton" style="height: 48px; margin-bottom: 8px; border-radius: 6px;"></div>
      </div>
      <div v-else-if="cases.length === 0" class="m-empty">
        <div class="m-empty-icon" aria-hidden="true">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
        </div>
        <div class="m-empty-title">{{ t('testCase.noData') }}</div>
        <div class="m-empty-desc">{{ t('testCase.noDataDesc') }}</div>
      </div>
      <el-table
        v-else
        class="cases-table"
        :data="cases"
        row-class-name="table-row"
        highlight-current-row
        @row-click="handleRowClick"
      >
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="env_id" :label="t('testCase.env')" width="100" />
        <el-table-column prop="question" :label="t('testCase.question')" show-overflow-tooltip />
        <el-table-column prop="golden_sql" :label="t('testCase.goldenSql')" show-overflow-tooltip>
          <template #default="{ row }">
            <code class="sql-inline">{{ row.golden_sql.slice(0, 60) }}{{ row.golden_sql.length > 60 ? '...' : '' }}</code>
          </template>
        </el-table-column>
        <el-table-column prop="tags" :label="t('testCase.tags')" width="160">
          <template #default="{ row }">
            <div class="tag-list">
              <span v-for="tag in (row.tags ?? [])" :key="tag" class="m-tag primary">{{ tag }}</span>
              <span v-if="!row.tags?.length" class="m-tag neutral">—</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column :label="t('task.actions')" width="130">
          <template #default="{ row }">
            <div class="action-btns">
              <button class="m-btn sm ghost" @click.stop="showEditDialog(row)" :aria-label="`编辑用例 ${row.id}`">
                {{ t('common.edit') }}
              </button>
              <button class="m-btn sm danger" @click.stop="handleDelete(row.id)" :aria-label="`删除用例 ${row.id}`">
                {{ t('common.delete') }}
              </button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 创建/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="560px">
      <el-form :model="form" label-width="100px">
        <el-form-item :label="t('testCase.env')" required>
          <el-select v-model="form.env_id" :placeholder="t('env.placeholder')" style="width:100%">
            <el-option v-for="env in environments" :key="env.id" :label="env.env_name" :value="env.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('testCase.question')" required>
          <el-input v-model="form.question" type="textarea" :rows="3" :placeholder="t('testCase.questionPlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('testCase.goldenSql')" required>
          <el-input v-model="form.golden_sql" type="textarea" :rows="4" :placeholder="t('testCase.sqlPlaceholder')" style="font-family: var(--font-mono)" />
        </el-form-item>
        <el-form-item :label="t('testCase.tags')">
          <el-input v-model="tagsInput" :placeholder="t('testCase.tagsPlaceholder')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <button class="m-btn secondary" @click="dialogVisible = false">{{ t('common.cancel') }}</button>
        <button class="m-btn primary" :class="{ 'is-loading': isSubmitting }" @click="submitForm" style="margin-left: 8px;">
          <span v-if="isSubmitting" class="m-spinner" aria-hidden="true"></span>
          {{ editingId ? t('common.edit') : t('common.add') }}
        </button>
      </template>
    </el-dialog>

    <!-- 批量导入对话框 -->
    <el-dialog v-model="batchVisible" :title="t('testCase.batchImport')" width="560px">
      <p style="font-size:13px;color:var(--m-text-muted);margin-bottom:12px;">
        每行一条记录，格式：<code class="sql-inline">问题|||SELECT xxx</code>（三竖线分隔）
      </p>
      <el-form label-width="80px">
        <el-form-item :label="t('testCase.env')" required>
          <el-select v-model="batchEnvId" :placeholder="t('env.placeholder')" style="width:100%">
            <el-option v-for="env in environments" :key="env.id" :label="env.env_name" :value="env.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="batchContent" type="textarea" :rows="8" placeholder="问题1|||SELECT * FROM t1&#10;问题2|||SELECT count(*) FROM t2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <button class="m-btn secondary" @click="batchVisible = false">{{ t('common.cancel') }}</button>
        <button class="m-btn primary" :class="{ 'is-loading': isBatchSubmitting }" @click="submitBatch" style="margin-left: 8px;">
          <span v-if="isBatchSubmitting" class="m-spinner" aria-hidden="true"></span>
          {{ t('common.add') }}
        </button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import type { TestCase, SchemaEnv } from '../types'
import { getTestCases, createTestCase, updateTestCase, deleteTestCase, createTestCasesBatch, getSchemaEnvs } from '../api'
import { t } from '../i18n'

const cases        = ref<TestCase[]>([])
const environments = ref<SchemaEnv[]>([])
const filterEnvId  = ref<number | undefined>(undefined)
const isLoading    = ref(true)
const isSubmitting = ref(false)
const isBatchSubmitting = ref(false)
const dialogVisible = ref(false)
const batchVisible  = ref(false)
const editingId     = ref<number | null>(null)
const tagsInput     = ref('')
const batchContent  = ref('')
const batchEnvId    = ref<number | undefined>(undefined)

const form = ref({ env_id: undefined as number | undefined, question: '', golden_sql: '', tags: [] as string[] })
const dialogTitle = computed(() => editingId.value ? t('common.edit') : t('common.add'))

const loadCases = async () => {
  isLoading.value = true
  try {
    const res = await getTestCases(filterEnvId.value)
    cases.value = res.data
  } catch { ElMessage.error(t('common.failed')) }
  finally { isLoading.value = false }
}

const showCreateDialog = () => {
  editingId.value = null
  form.value = { env_id: undefined, question: '', golden_sql: '', tags: [] }
  tagsInput.value = ''
  dialogVisible.value = true
}

const showEditDialog = (row: TestCase) => {
  editingId.value = row.id
  form.value = { env_id: row.env_id, question: row.question, golden_sql: row.golden_sql, tags: row.tags ?? [] }
  tagsInput.value = (row.tags ?? []).join(', ')
  dialogVisible.value = true
}

const showBatchCreate = () => {
  batchContent.value = ''
  batchEnvId.value = undefined
  batchVisible.value = true
}

const submitForm = async () => {
  if (!form.value.env_id || !form.value.question || !form.value.golden_sql) {
    ElMessage.warning('请填写必填项')
    return
  }
  isSubmitting.value = true
  try {
    const data = {
      ...form.value,
      tags: tagsInput.value ? tagsInput.value.split(',').map(s => s.trim()).filter(Boolean) : [],
    }
    if (editingId.value) {
      await updateTestCase(editingId.value, data)
      ElMessage.success(t('common.success'))
    } else {
      await createTestCase(data)
      ElMessage.success(t('common.success'))
    }
    dialogVisible.value = false
    await loadCases()
  } catch { ElMessage.error(t('common.failed')) }
  finally { isSubmitting.value = false }
}

const submitBatch = async () => {
  if (!batchEnvId.value || !batchContent.value.trim()) {
    ElMessage.warning('请填写环境和内容')
    return
  }
  isBatchSubmitting.value = true
  try {
    const rows = batchContent.value.trim().split('\n')
      .map(line => {
        const [question, golden_sql] = line.split('|||')
        return question && golden_sql ? { env_id: batchEnvId.value!, question: question.trim(), golden_sql: golden_sql.trim(), tags: [] } : null
      })
      .filter(Boolean) as typeof form.value[]
    await createTestCasesBatch(rows)
    ElMessage.success(`成功导入 ${rows.length} 条用例`)
    batchVisible.value = false
    await loadCases()
  } catch { ElMessage.error(t('common.failed')) }
  finally { isBatchSubmitting.value = false }
}

const handleDelete = async (id: number) => {
  try {
    await deleteTestCase(id)
    ElMessage.success(t('common.success'))
    await loadCases()
  } catch { ElMessage.error(t('common.failed')) }
}

const handleRowClick = (_row: TestCase) => { /* 点击行可扩展查看详情 */ }

onMounted(async () => {
  await Promise.all([
    loadCases(),
    getSchemaEnvs().then(r => environments.value = r.data),
  ])
})
</script>

<style scoped>
.testcase-page {
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
  flex-wrap: wrap;
  gap: 12px;
}

.page-heading {
  font-size: 20px;
  font-weight: 700;
  color: var(--m-text);
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.table-card {
  padding: 10px;
  border-radius: var(--radius-2xl);
  background:
    linear-gradient(160deg, rgba(16, 185, 129, 0.04), rgba(59, 130, 246, 0.03)),
    var(--m-surface);
  border-color: rgba(255, 255, 255, 0.12);
  box-shadow: var(--m-shadow-lg);
  overflow: hidden;
}

[data-theme="light"] .table-card {
  border-color: rgba(0, 0, 0, 0.12);
  background:
    linear-gradient(160deg, rgba(16, 185, 129, 0.08), rgba(59, 130, 246, 0.05)),
    #fff;
}

:deep(.cases-table) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-row-hover-bg-color: rgba(16, 185, 129, 0.1);
  --el-table-current-row-bg-color: rgba(16, 185, 129, 0.13);
  --el-table-header-bg-color: rgba(255, 255, 255, 0.06);
  --el-table-border-color: rgba(255, 255, 255, 0.08);
  --el-table-text-color: var(--m-text);
  --el-table-header-text-color: var(--m-text-muted);
  border-radius: var(--radius-xl);
  border: 1px solid rgba(255, 255, 255, 0.08);
  overflow: hidden;
}

[data-theme="light"] :deep(.cases-table) {
  --el-table-header-bg-color: rgba(0, 0, 0, 0.04);
  --el-table-border-color: rgba(0, 0, 0, 0.08);
  border-color: rgba(0, 0, 0, 0.08);
}

:deep(.cases-table .el-table__header-wrapper th) {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.25px;
  text-transform: uppercase;
}

:deep(.cases-table .el-table__cell) {
  padding-top: 12px;
  padding-bottom: 12px;
}

:deep(.cases-table .el-table__row) {
  transition: background-color var(--t-fast);
}

/* 表格行：cursor-pointer，满足规范 */
:deep(.table-row) {
  cursor: pointer;
}

:deep(.table-row:hover td) {
  background: var(--m-surface-hover) !important;
}

.sql-inline {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--m-primary);
  background: rgba(16, 185, 129, 0.14);
  border: 1px solid rgba(16, 185, 129, 0.24);
  padding: 2px 7px;
  border-radius: 6px;
  font-weight: 600;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.action-btns {
  display: flex;
  gap: 6px;
}

@media (max-width: 1100px) {
  .toolbar-right {
    width: 100%;
    justify-content: flex-start;
  }
}

@media (max-width: 768px) {
  .page-toolbar {
    align-items: flex-start;
  }

  .page-heading {
    font-size: 18px;
  }

  :deep(.cases-table .el-table__cell) {
    padding-top: 10px;
    padding-bottom: 10px;
  }

  .action-btns {
    flex-wrap: wrap;
  }
}
</style>
