<template>
  <div class="env-page">
    <div class="page-toolbar">
      <h1 class="page-heading">{{ t('env.title') }}</h1>
      <button class="m-btn primary" @click="showCreateDialog" aria-label="新建数据库环境">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        {{ t('env.createEnv') }}
      </button>
    </div>

    <!-- 骨架屏 -->
    <div v-if="isLoading" class="env-list">
      <div v-for="i in 3" :key="i" class="m-skeleton" style="height: 100px; border-radius: 12px;"></div>
    </div>

    <!-- 空状态 -->
    <div v-else-if="envs.length === 0" class="m-empty" style="margin-top: 40px;">
      <div class="m-empty-icon" aria-hidden="true">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
      </div>
      <div class="m-empty-title">{{ t('env.noEnvs') }}</div>
      <div class="m-empty-desc">{{ t('env.noEnvsDesc') }}</div>
    </div>

    <!-- 环境列表 -->
    <div v-else class="env-list" role="list">
      <article
        v-for="env in envs"
        :key="env.id"
        class="m-card env-card"
        role="listitem"
        :aria-label="`数据库环境: ${env.env_name}`"
      >
        <!-- 环境头部 -->
        <div class="env-header">
          <div class="env-icon" aria-hidden="true">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
          </div>
          <div class="env-meta">
            <div class="env-name">{{ env.env_name }}</div>
            <div class="env-id font-mono">ID #{{ env.id }}</div>
          </div>
          <div class="env-header-right">
            <span v-if="env.sandbox_db_url" class="m-tag success">Sandbox</span>
            <span v-else class="m-tag neutral">No Sandbox</span>
          </div>
        </div>

        <!-- DDL 代码块 -->
        <div class="ddl-section">
          <div class="ddl-header">
            <span class="ddl-label">DDL Schema</span>
            <button
              class="m-btn sm ghost copy-btn"
              @click="copyDDL(env)"
              :aria-label="`复制 ${env.env_name} 的 DDL`"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
              {{ copiedId === env.id ? '已复制!' : t('common.copy') }}
            </button>
          </div>
          <pre class="m-code ddl-code">{{ truncateDDL(env.ddl_content) }}</pre>
          <button
            v-if="env.ddl_content.length > 300"
            class="m-btn sm ghost expand-btn"
            @click="selectedEnv = env; ddlDialogVisible = true"
          >
            查看完整 DDL ({{ env.ddl_content.length }} 字符)
          </button>
        </div>

        <!-- 操作 -->
        <div class="env-actions">
          <button class="m-btn sm secondary" style="flex:1" @click="showEditDialog(env)" :aria-label="`编辑 ${env.env_name}`">
            {{ t('common.edit') }}
          </button>
          <button class="m-btn sm danger" @click="handleDelete(env)" :aria-label="`删除 ${env.env_name}`">
            {{ t('common.delete') }}
          </button>
        </div>
      </article>
    </div>

    <!-- 创建/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? t('common.edit') : t('env.createEnv')" width="600px">
      <el-form :model="form" label-width="120px">
        <el-form-item :label="t('env.name')" required>
          <el-input v-model="form.env_name" :placeholder="t('env.namePlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('env.ddl')" required>
          <el-input
            v-model="form.ddl_content"
            type="textarea"
            :rows="8"
            :placeholder="t('env.ddlPlaceholder')"
            style="font-family: var(--font-mono); font-size: 12px;"
          />
        </el-form-item>
        <el-form-item :label="t('env.sandboxUrl')">
          <el-input v-model="form.sandbox_db_url" placeholder="postgresql://user:pass@host:5432/dbname（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <button class="m-btn secondary" @click="dialogVisible = false">{{ t('common.cancel') }}</button>
        <button class="m-btn primary" :class="{ 'is-loading': isSubmitting }" @click="submitForm" style="margin-left: 8px;">
          <span v-if="isSubmitting" class="m-spinner" aria-hidden="true"></span>
          {{ t('common.save') }}
        </button>
      </template>
    </el-dialog>

    <!-- 完整 DDL 展示对话框 -->
    <el-dialog v-model="ddlDialogVisible" :title="`${selectedEnv?.env_name} - DDL`" width="70%">
      <div class="ddl-full-header">
        <button class="m-btn sm ghost" @click="selectedEnv && copyDDL(selectedEnv)">
          {{ selectedEnv && copiedId === selectedEnv.id ? '已复制!' : t('common.copy') }}
        </button>
      </div>
      <pre class="m-code" style="max-height: 500px;">{{ selectedEnv?.ddl_content }}</pre>
    </el-dialog>

    <!-- 删除确认 -->
    <el-dialog v-model="confirmVisible" :title="t('common.confirmDelete')" width="380px">
      <p style="font-size:14px;color:var(--m-text-muted);">
        确认删除环境「{{ deletingEnv?.env_name }}」？删除后数据无法恢复。
      </p>
      <template #footer>
        <button class="m-btn secondary" @click="confirmVisible = false">{{ t('common.cancel') }}</button>
        <button class="m-btn danger" :class="{ 'is-loading': isDeleting }" @click="confirmDelete" style="margin-left: 8px;">
          <span v-if="isDeleting" class="m-spinner" aria-hidden="true"></span>
          {{ t('common.delete') }}
        </button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import type { SchemaEnv } from '../types'
import { getSchemaEnvs, createSchemaEnv, updateSchemaEnv, deleteSchemaEnv } from '../api'
import { t } from '../i18n'

const envs = ref<SchemaEnv[]>([])
const isLoading    = ref(true)
const isSubmitting = ref(false)
const isDeleting   = ref(false)
const dialogVisible  = ref(false)
const ddlDialogVisible = ref(false)
const confirmVisible = ref(false)
const editingId    = ref<number | null>(null)
const deletingEnv  = ref<SchemaEnv | null>(null)
const selectedEnv  = ref<SchemaEnv | null>(null)
const copiedId     = ref<number | null>(null)

const form = ref({
  env_name: '',
  ddl_content: '',
  sandbox_db_url: '',
})

const loadEnvs = async () => {
  isLoading.value = true
  try {
    const res = await getSchemaEnvs()
    envs.value = res.data
  } catch { ElMessage.error(t('common.failed')) }
  finally { isLoading.value = false }
}

const showCreateDialog = () => {
  editingId.value = null
  form.value = { env_name: '', ddl_content: '', sandbox_db_url: '' }
  dialogVisible.value = true
}

const showEditDialog = (env: SchemaEnv) => {
  editingId.value = env.id
  form.value = { env_name: env.env_name, ddl_content: env.ddl_content, sandbox_db_url: env.sandbox_db_url ?? '' }
  dialogVisible.value = true
}

const submitForm = async () => {
  if (!form.value.env_name || !form.value.ddl_content) {
    ElMessage.warning('请填写必填项')
    return
  }
  isSubmitting.value = true
  try {
    const data = { ...form.value, sandbox_db_url: form.value.sandbox_db_url || undefined }
    if (editingId.value) {
      await updateSchemaEnv(editingId.value, data)
    } else {
      await createSchemaEnv(data)
    }
    ElMessage.success(t('common.success'))
    dialogVisible.value = false
    await loadEnvs()
  } catch { ElMessage.error(t('common.failed')) }
  finally { isSubmitting.value = false }
}

const handleDelete = (env: SchemaEnv) => {
  deletingEnv.value = env
  confirmVisible.value = true
}

const confirmDelete = async () => {
  if (!deletingEnv.value) return
  isDeleting.value = true
  try {
    await deleteSchemaEnv(deletingEnv.value.id)
    ElMessage.success(t('common.success'))
    confirmVisible.value = false
    await loadEnvs()
  } catch { ElMessage.error(t('common.failed')) }
  finally { isDeleting.value = false }
}

/** DDL 截断预览 */
const truncateDDL = (ddl: string) => ddl.length > 300 ? ddl.slice(0, 300) + '\n…（点击查看完整）' : ddl

/** 复制 DDL 到剪贴板 */
const copyDDL = async (env: SchemaEnv) => {
  try {
    await navigator.clipboard.writeText(env.ddl_content)
    copiedId.value = env.id
    setTimeout(() => copiedId.value = null, 2000)
  } catch {
    ElMessage.error('复制失败，请手动复制')
  }
}

onMounted(loadEnvs)
</script>

<style scoped>
.env-page {
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

.env-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.env-card {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* 头部 */
.env-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.env-icon {
  width: 38px;
  height: 38px;
  border-radius: var(--radius-lg);
  background: var(--m-primary-ghost);
  color: var(--m-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.env-meta { flex: 1; min-width: 0; }

.env-name {
  font-size: 15px;
  font-weight: 700;
  color: var(--m-text);
}

.env-id {
  font-size: 11px;
  color: var(--m-text-dim);
  margin-top: 2px;
}

.env-header-right { margin-left: auto; }

/* DDL */
.ddl-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: var(--m-surface-bright);
  border-radius: var(--radius-lg);
  padding: 12px;
}

.ddl-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.ddl-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--m-text-muted);
}

.ddl-code {
  max-height: 120px;
  font-size: 11px;
  overflow: hidden;
}

.expand-btn {
  font-size: 11px;
  color: var(--m-primary);
  align-self: flex-start;
}

.copy-btn {
  min-height: unset;
  padding: 3px 8px;
}

.ddl-full-header {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 10px;
}

/* 操作 */
.env-actions {
  display: flex;
  gap: 8px;
  border-top: 1px solid var(--m-border);
  padding-top: 12px;
}

.font-mono { font-family: var(--font-mono); }

[data-theme="light"] .env-page :deep(.m-code) {
  background: #ffffff;
  color: #0f172a;
  border: 1px solid rgba(15, 23, 42, 0.12);
}
</style>
