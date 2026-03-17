<template>
  <div class="agent-page">
    <div class="page-toolbar">
      <h1 class="page-heading">{{ t('agent.title') }}</h1>
      <button class="m-btn primary" @click="showCreateDialog" aria-label="新建 Agent 配置">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        {{ t('agent.createAgent') }}
      </button>
    </div>

    <!-- 骨架屏 -->
    <div v-if="isLoading" class="agent-grid">
      <div v-for="i in 4" :key="i" class="m-skeleton" style="height: 160px; border-radius: 12px;"></div>
    </div>

    <!-- 空状态 -->
    <div v-else-if="agents.length === 0" class="m-empty" style="margin-top: 40px;">
      <div class="m-empty-icon" aria-hidden="true">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"/></svg>
      </div>
      <div class="m-empty-title">{{ t('agent.noAgents') }}</div>
      <div class="m-empty-desc">{{ t('agent.noAgentsDesc') }}</div>
    </div>

    <!-- Agent 卡片网格 -->
    <div v-else class="agent-grid" role="list">
      <article
        v-for="agent in agents"
        :key="agent.id"
        class="m-card agent-card"
        role="listitem"
        :aria-label="`Agent: ${agent.agent_name}`"
      >
        <!-- 卡片 Header -->
        <div class="agent-header">
          <div class="agent-avatar" aria-hidden="true">
            {{ agent.agent_name.charAt(0).toUpperCase() }}
          </div>
          <div class="agent-title-block">
            <div class="agent-name">{{ agent.agent_name }}</div>
            <div class="agent-id font-mono">ID #{{ agent.id }}</div>
          </div>
          <span class="m-tag success agent-badge">Active</span>
        </div>

        <!-- 端点信息 -->
        <div class="agent-endpoint">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
          <span class="endpoint-url">{{ maskEndpoint(agent.api_endpoint) }}</span>
        </div>

        <!-- 参数指标 -->
        <div class="agent-metrics">
          <div class="metric">
            <div class="metric-label">QPS</div>
            <div class="metric-val font-mono">{{ agent.rate_limit_qps }}</div>
          </div>
          <div class="metric">
            <div class="metric-label">Timeout</div>
            <div class="metric-val font-mono">{{ agent.timeout_ms }}<small>ms</small></div>
          </div>
          <div class="metric">
            <div class="metric-label">Token</div>
            <div class="metric-val">{{ agent.auth_token ? '••••••' : '—' }}</div>
          </div>
        </div>

        <!-- 操作 -->
        <div class="agent-actions">
          <button class="m-btn sm secondary" style="flex:1" @click="showEditDialog(agent)" :aria-label="`编辑 ${agent.agent_name}`">
            {{ t('common.edit') }}
          </button>
          <button class="m-btn sm danger" @click="handleDelete(agent)" :aria-label="`删除 ${agent.agent_name}`">
            {{ t('common.delete') }}
          </button>
        </div>
      </article>
    </div>

    <!-- 创建/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? t('common.edit') : t('agent.createAgent')" width="500px">
      <el-form :model="form" label-width="110px">
        <el-form-item :label="t('agent.name')" required>
          <el-input v-model="form.agent_name" :placeholder="t('agent.namePlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('agent.endpoint')" required>
          <el-input v-model="form.api_endpoint" placeholder="https://api.example.com/v1" />
        </el-form-item>
        <el-form-item :label="t('agent.token')">
          <el-input v-model="form.auth_token" type="password" show-password :placeholder="t('agent.tokenPlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('agent.rateLimit')">
          <el-input-number v-model="form.rate_limit_qps" :min="1" :max="100" style="width:100%" />
        </el-form-item>
        <el-form-item :label="t('agent.timeout')">
          <el-input-number v-model="form.timeout_ms" :min="1000" :max="300000" :step="1000" style="width:100%" />
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

    <!-- 删除确认 -->
    <el-dialog v-model="confirmVisible" :title="t('common.confirmDelete')" width="380px">
      <p style="font-size:14px;color:var(--m-text-muted);">
        确认删除 Agent「{{ deletingAgent?.agent_name }}」？此操作不可撤销。
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
import type { AgentConfig } from '../types'
import { getAgents, createAgent, updateAgent, deleteAgent } from '../api'
import { t } from '../i18n'

const agents       = ref<AgentConfig[]>([])
const isLoading    = ref(true)
const isSubmitting = ref(false)
const isDeleting   = ref(false)
const dialogVisible = ref(false)
const confirmVisible = ref(false)
const editingId    = ref<number | null>(null)
const deletingAgent = ref<AgentConfig | null>(null)

const form = ref({
  agent_name: '',
  api_endpoint: '',
  auth_token: '',
  rate_limit_qps: 5,
  timeout_ms: 30000,
})

const loadAgents = async () => {
  isLoading.value = true
  try {
    const res = await getAgents()
    agents.value = res.data
  } catch { ElMessage.error(t('common.failed')) }
  finally { isLoading.value = false }
}

const showCreateDialog = () => {
  editingId.value = null
  form.value = { agent_name: '', api_endpoint: '', auth_token: '', rate_limit_qps: 5, timeout_ms: 30000 }
  dialogVisible.value = true
}

const showEditDialog = (agent: AgentConfig) => {
  editingId.value = agent.id
  form.value = {
    agent_name: agent.agent_name,
    api_endpoint: agent.api_endpoint,
    auth_token: agent.auth_token ?? '',
    rate_limit_qps: agent.rate_limit_qps,
    timeout_ms: agent.timeout_ms,
  }
  dialogVisible.value = true
}

const submitForm = async () => {
  if (!form.value.agent_name || !form.value.api_endpoint) {
    ElMessage.warning('请填写必填项')
    return
  }
  isSubmitting.value = true
  try {
    const data = { ...form.value, auth_token: form.value.auth_token || undefined }
    if (editingId.value) {
      await updateAgent(editingId.value, data)
    } else {
      await createAgent(data)
    }
    ElMessage.success(t('common.success'))
    dialogVisible.value = false
    await loadAgents()
  } catch { ElMessage.error(t('common.failed')) }
  finally { isSubmitting.value = false }
}

const handleDelete = (agent: AgentConfig) => {
  deletingAgent.value = agent
  confirmVisible.value = true
}

const confirmDelete = async () => {
  if (!deletingAgent.value) return
  isDeleting.value = true
  try {
    await deleteAgent(deletingAgent.value.id)
    ElMessage.success(t('common.success'))
    confirmVisible.value = false
    await loadAgents()
  } catch { ElMessage.error(t('common.failed')) }
  finally { isDeleting.value = false }
}

/** 脱敏显示端点 URL */
const maskEndpoint = (url: string) => {
  try {
    const u = new URL(url)
    return `${u.protocol}//${u.hostname}/...`
  } catch { return url.slice(0, 40) + '...' }
}

onMounted(loadAgents)
</script>

<style scoped>
.agent-page {
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

/* 卡片网格 */
.agent-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.agent-card {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.agent-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.agent-avatar {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-xl);
  background: var(--m-primary-ghost);
  color: var(--m-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 700;
  flex-shrink: 0;
}

.agent-title-block { flex: 1; min-width: 0; }

.agent-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--m-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.agent-id {
  font-size: 11px;
  color: var(--m-text-dim);
  margin-top: 2px;
}

.agent-badge { margin-left: auto; flex-shrink: 0; }

/* 端点 */
.agent-endpoint {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--m-surface-bright);
  border-radius: var(--radius-md);
  padding: 8px 10px;
}

.endpoint-url {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--m-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 指标 */
.agent-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  border-top: 1px solid var(--m-border);
  padding-top: 14px;
}

.metric {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.metric-label {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--m-text-dim);
}

.metric-val {
  font-size: 16px;
  font-weight: 700;
  color: var(--m-text);
}

.metric-val small {
  font-size: 10px;
  opacity: 0.5;
}

/* 操作 */
.agent-actions {
  display: flex;
  gap: 8px;
  border-top: 1px solid var(--m-border);
  padding-top: 12px;
}

.font-mono { font-family: var(--font-mono); }
</style>
