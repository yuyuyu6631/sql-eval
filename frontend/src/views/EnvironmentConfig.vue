<template>
  <div class="environment-config">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ t('env.title') }}</span>
          <el-button type="primary" @click="showCreateDialog">{{ t('env.createEnv') }}</el-button>
        </div>
      </template>

      <el-table :data="environments" v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="env_name" :label="t('env.name')" />
        <el-table-column prop="ddl_content" :label="t('env.ddl')" show-overflow-tooltip />
        <el-table-column prop="created_at" :label="t('task.startTime')" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column :label="t('common.operation')" width="200">
          <template #default="{ row }">
            <el-button size="small" @click="editEnv(row)">{{ t('common.edit') }}</el-button>
            <el-button size="small" type="danger" @click="deleteEnv(row.id)">{{ t('common.delete') }}</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? t('env.editEnv') : t('env.createEnv')"
      width="600px"
    >
      <el-form :model="form" label-width="120px">
        <el-form-item :label="t('env.name')">
          <el-input v-model="form.env_name" :placeholder="t('env.placeholder')" />
        </el-form-item>
        <el-form-item :label="t('env.ddl')">
          <el-input
            v-model="form.ddl_content"
            type="textarea"
            :rows="10"
            :placeholder="t('env.placeholder')"
          />
        </el-form-item>
        <el-form-item :label="t('env.dbUrl')">
          <el-input v-model="form.sandbox_db_url" :placeholder="t('env.placeholder')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="submitForm">{{ t('env.submit') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getSchemaEnvs, createSchemaEnv, updateSchemaEnv, deleteSchemaEnv } from '../api'
import type { SchemaEnv } from '../types'
import { t } from '../i18n'

const environments = ref<SchemaEnv[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref<number>()

const form = ref({
  env_name: '',
  ddl_content: '',
  sandbox_db_url: '',
})

const loadEnvironments = async () => {
  loading.value = true
  try {
    const res = await getSchemaEnvs()
    environments.value = res.data
  } catch (error) {
    ElMessage.error(t('common.failed'))
  } finally {
    loading.value = false
  }
}

const showCreateDialog = () => {
  isEdit.value = false
  form.value = { env_name: '', ddl_content: '', sandbox_db_url: '' }
  dialogVisible.value = true
}

const editEnv = (env: SchemaEnv) => {
  isEdit.value = true
  editId.value = env.id
  form.value = {
    env_name: env.env_name,
    ddl_content: env.ddl_content,
    sandbox_db_url: env.sandbox_db_url || '',
  }
  dialogVisible.value = true
}

const submitForm = async () => {
  try {
    if (isEdit.value && editId.value) {
      await updateSchemaEnv(editId.value, form.value)
      ElMessage.success(t('env.updateSuccess'))
    } else {
      await createSchemaEnv(form.value)
      ElMessage.success(t('env.createSuccess'))
    }
    dialogVisible.value = false
    loadEnvironments()
  } catch (error) {
    ElMessage.error(t('common.failed'))
  }
}

const deleteEnv = async (id: number) => {
  try {
    await deleteSchemaEnv(id)
    ElMessage.success(t('env.deleteSuccess'))
    loadEnvironments()
  } catch (error) {
    ElMessage.error(t('common.failed'))
  }
}

const formatDate = (date: string) => {
  return new Date(date).toLocaleString()
}

onMounted(() => {
  loadEnvironments()
})
</script>

<style scoped>
.environment-config {
  /* padding: 20px; 已由 App.vue 统一管理 */
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
