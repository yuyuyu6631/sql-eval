<template>
  <div class="test-case-manage">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ t('testCase.title') }}</span>
          <div>
            <el-button type="primary" @click="showCreateDialog">{{ t('testCase.addCase') }}</el-button>
            <el-button @click="showGenerateDialog">{{ t('testCase.aiGenerate') }}</el-button>
          </div>
        </div>
      </template>

      <div class="filters">
        <el-select v-model="filterEnvId" :placeholder="t('testCase.filterEnv')" clearable @change="loadCases">
          <el-option v-for="env in environments" :key="env.id" :label="env.env_name" :value="env.id" />
        </el-select>
      </div>

      <el-table :data="testCases" v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="question" :label="t('testCase.question')" show-overflow-tooltip />
        <el-table-column prop="golden_sql" :label="t('testCase.goldenSql')" show-overflow-tooltip />
        <el-table-column prop="tags" :label="t('testCase.tags')">
          <template #default="{ row }">
            <el-tag v-for="tag in row.tags" :key="tag" size="small" style="margin-right: 5px">
              {{ tag }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('common.operation')" width="200">
          <template #default="{ row }">
            <el-button size="small" @click="editCase(row)">{{ t('common.edit') }}</el-button>
            <el-button size="small" type="danger" @click="deleteCase(row.id)">{{ t('common.delete') }}</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="isEdit ? t('testCase.editCase') : t('testCase.addCase')" width="600px">
      <el-form :model="form" label-width="100px">
        <el-form-item :label="t('common.environment')">
          <el-select v-model="form.env_id" :placeholder="t('env.placeholder')">
            <el-option v-for="env in environments" :key="env.id" :label="env.env_name" :value="env.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('testCase.question')">
          <el-input v-model="form.question" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item :label="t('testCase.goldenSql')">
          <el-input v-model="form.golden_sql" type="textarea" :rows="5" />
        </el-form-item>
        <el-form-item :label="t('testCase.tags')">
          <el-input v-model="tagsInput" :placeholder="t('testCase.tagsPlaceholder')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="submitForm">{{ t('common.submit') }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="generateDialogVisible" :title="t('testCase.genTitle')" width="400px">
      <el-form :model="generateForm" label-width="100px">
        <el-form-item :label="t('common.environment')">
          <el-select v-model="generateForm.env_id" :placeholder="t('env.placeholder')">
            <el-option v-for="env in environments" :key="env.id" :label="env.env_name" :value="env.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('testCase.genCount')">
          <el-input-number v-model="generateForm.count" :min="1" :max="20" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="generateDialogVisible = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="generateCases">{{ t('testCase.genBtn') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getTestCases, createTestCase, updateTestCase, deleteTestCase, generateTestCases, getSchemaEnvs } from '../api'
import type { TestCase, SchemaEnv } from '../types'
import { t } from '../i18n'

const testCases = ref<TestCase[]>([])
const environments = ref<SchemaEnv[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const generateDialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref<number>()
const filterEnvId = ref<number>()
const tagsInput = ref('')

const form = ref({
  env_id: undefined as number | undefined,
  question: '',
  golden_sql: '',
  tags: [] as string[],
})

const generateForm = ref({
  env_id: undefined as number | undefined,
  count: 5,
})

const loadCases = async () => {
  loading.value = true
  try {
    const res = await getTestCases(filterEnvId.value)
    testCases.value = res.data
  } catch (error) {
    ElMessage.error(t('common.failed'))
  } finally {
    loading.value = false
  }
}

const loadEnvironments = async () => {
  const res = await getSchemaEnvs()
  environments.value = res.data
}

const showCreateDialog = () => {
  isEdit.value = false
  form.value = { env_id: undefined, question: '', golden_sql: '', tags: [] }
  tagsInput.value = ''
  dialogVisible.value = true
}

const editCase = (caseItem: TestCase) => {
  isEdit.value = true
  editId.value = caseItem.id
  form.value = {
    env_id: caseItem.env_id,
    question: caseItem.question,
    golden_sql: caseItem.golden_sql,
    tags: caseItem.tags || [],
  }
  tagsInput.value = (caseItem.tags || []).join(', ')
  dialogVisible.value = true
}

const submitForm = async () => {
  form.value.tags = tagsInput.value.split(',').map(t => t.trim()).filter(Boolean)
  try {
    if (isEdit.value && editId.value) {
      await updateTestCase(editId.value, form.value)
      ElMessage.success(t('testCase.updateSuccess'))
    } else {
      await createTestCase(form.value)
      ElMessage.success(t('testCase.createSuccess'))
    }
    dialogVisible.value = false
    loadCases()
  } catch (error) {
    ElMessage.error(t('common.failed'))
  }
}

const deleteCase = async (id: number) => {
  try {
    await deleteTestCase(id)
    ElMessage.success(t('testCase.deleteSuccess'))
    loadCases()
  } catch (error) {
    ElMessage.error(t('common.failed'))
  }
}

const showGenerateDialog = () => {
  generateForm.value = { env_id: undefined, count: 5 }
  generateDialogVisible.value = true
}

const generateCases = async () => {
  try {
    await generateTestCases(generateForm.value)
    ElMessage.success(t('testCase.genSuccess'))
    generateDialogVisible.value = false
    loadCases()
  } catch (error) {
    ElMessage.error(t('common.failed'))
  }
}

onMounted(() => {
  loadCases()
  loadEnvironments()
})
</script>

<style scoped>
.test-case-manage {
  /* padding: 20px; 已由 App.vue 统一管理 */
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filters {
  margin-bottom: 20px;
}

.filters .el-select {
  width: 300px;
}
</style>
