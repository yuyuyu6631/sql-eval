<template>
  <div class="agent-config">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ t('agent.title') }}</span>
          <el-button type="primary" @click="showCreateDialog">{{ t('agent.addAgent') }}</el-button>
        </div>
      </template>

      <el-table :data="agents" v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="agent_name" :label="t('agent.name')" />
        <el-table-column prop="api_endpoint" :label="t('agent.endpoint')" show-overflow-tooltip />
        <el-table-column prop="rate_limit_qps" :label="t('agent.qps')" width="150" />
        <el-table-column prop="timeout_ms" :label="t('agent.timeout')" width="150" />
        <el-table-column :label="t('common.operation')" width="200">
          <template #default="{ row }">
            <el-button size="small" @click="editAgent(row)">{{ t('common.edit') }}</el-button>
            <el-button size="small" type="danger" @click="deleteAgent(row.id)">{{ t('common.delete') }}</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="isEdit ? t('agent.editAgent') : t('agent.addAgent')" width="600px">
      <el-form :model="form" label-width="120px">
        <el-form-item :label="t('agent.name')">
          <el-input v-model="form.agent_name" placeholder="e.g., GPT-4 SQL Agent" />
        </el-form-item>
        <el-form-item :label="t('agent.endpoint')">
          <el-input v-model="form.api_endpoint" placeholder="https://api.example.com/v1/sql" />
        </el-form-item>
        <el-form-item :label="t('agent.authToken')">
          <el-input v-model="form.auth_token" type="password" :placeholder="t('agent.tokenPlaceholder')" show-password />
        </el-form-item>
        <el-form-item :label="t('agent.qps')">
          <el-input-number v-model="form.rate_limit_qps" :min="1" :max="100" />
        </el-form-item>
        <el-form-item :label="t('agent.timeout')">
          <el-input-number v-model="form.timeout_ms" :min="1000" :max="120000" :step="1000" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="submitForm">{{ t('common.submit') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getAgents, createAgent, updateAgent, deleteAgent } from '../api'
import type { AgentConfig } from '../types'
import { t } from '../i18n'

const agents = ref<AgentConfig[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref<number>()

const form = ref({
  agent_name: '',
  api_endpoint: '',
  auth_token: '',
  rate_limit_qps: 10,
  timeout_ms: 30000,
})

const loadAgents = async () => {
  loading.value = true
  try {
    const res = await getAgents()
    agents.value = res.data
  } catch (error) {
    ElMessage.error(t('common.failed'))
  } finally {
    loading.value = false
  }
}

const showCreateDialog = () => {
  isEdit.value = false
  form.value = { agent_name: '', api_endpoint: '', auth_token: '', rate_limit_qps: 10, timeout_ms: 30000 }
  dialogVisible.value = true
}

const editAgent = (agent: AgentConfig) => {
  isEdit.value = true
  editId.value = agent.id
  form.value = {
    agent_name: agent.agent_name,
    api_endpoint: agent.api_endpoint,
    auth_token: agent.auth_token || '',
    rate_limit_qps: agent.rate_limit_qps,
    timeout_ms: agent.timeout_ms,
  }
  dialogVisible.value = true
}

const submitForm = async () => {
  try {
    if (isEdit.value && editId.value) {
      await updateAgent(editId.value, form.value)
      ElMessage.success(t('agent.updateSuccess'))
    } else {
      await createAgent(form.value)
      ElMessage.success(t('agent.createSuccess'))
    }
    dialogVisible.value = false
    loadAgents()
  } catch (error) {
    ElMessage.error(t('common.failed'))
  }
}

const deleteAgent = async (id: number) => {
  try {
    await deleteAgent(id)
    ElMessage.success(t('agent.deleteSuccess'))
    loadAgents()
  } catch (error) {
    ElMessage.error(t('common.failed'))
  }
}

onMounted(() => {
  loadAgents()
})
</script>

<style scoped>
.agent-config {
  /* padding: 20px; 已由 App.vue 统一管理 */
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
