<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #409eff">
              <el-icon :size="30"><Document /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.total_tasks || 0 }}</div>
              <div class="stat-label">{{ t('dashboard.totalTasks') }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #67c23a">
              <el-icon :size="30"><List /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.total_cases || 0 }}</div>
              <div class="stat-label">{{ t('dashboard.testCases') }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #e6a23c">
              <el-icon :size="30"><DataAnalysis /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.total_results || 0 }}</div>
              <div class="stat-label">{{ t('dashboard.results') }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #f56c6c">
              <el-icon :size="30"><CircleCheck /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.pass_rate || 0 }}%</div>
              <div class="stat-label">{{ t('dashboard.passRate') }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="8">
        <el-card>
          <template #header>
            <span>{{ t('dashboard.statusDistribution') }}</span>
          </template>
          <div class="chart-container">
            <Pie :data="pieData" :options="pieOptions" />
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header>
            <span>{{ t('dashboard.errorDistribution') }}</span>
          </template>
          <div class="chart-container">
            <Pie :data="errorPieData" :options="pieOptions" />
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header>
            <span>{{ t('dashboard.complexityAnalysis') }}</span>
          </template>
          <div class="complexity-info">
            <div class="complexity-item">
              <span class="label">{{ t('dashboard.avgExecutionTime') }}:</span>
              <span class="value">{{ complexity.avg_execution_time_ms }}ms</span>
            </div>
            <div class="complexity-item">
              <span class="label">{{ t('dashboard.slowestQuery') }}:</span>
              <span class="value">{{ complexity.slowest_query_ms }}ms</span>
            </div>
            <div class="complexity-item">
              <span class="label">{{ t('dashboard.fastestQuery') }}:</span>
              <span class="value">{{ complexity.fastest_query_ms }}ms</span>
            </div>
            <div class="complexity-item">
              <span class="label">{{ t('dashboard.totalQueries') }}:</span>
              <span class="value">{{ complexity.total_queries }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { Pie } from 'vue-chartjs'
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
} from 'chart.js'
import { Document, List, DataAnalysis, CircleCheck } from '@element-plus/icons-vue'
import { getDashboardStats, getComplexityAnalysis, getErrorDistribution } from '../api'
import { t } from '../i18n'

ChartJS.register(ArcElement, Tooltip, Legend)

const stats = ref<any>({})
const complexity = ref<any>({})
const errorDist = ref<any>({})

const pieData = computed(() => ({
  labels: Object.keys(stats.value.status_counts || {}),
  datasets: [
    {
      data: Object.values(stats.value.status_counts || {}),
      backgroundColor: ['#67c23a', '#409eff', '#e6a23c', '#f56c6c'],
    },
  ],
}))

const errorPieData = computed(() => ({
  labels: Object.keys(errorDist.value || {}),
  datasets: [
    {
      data: Object.values(errorDist.value || {}),
      backgroundColor: ['#f56c6c', '#e6a23c', '#409eff', '#909399'],
    },
  ],
}))

const pieOptions = {
  responsive: true,
  maintainAspectRatio: false,
}

onMounted(async () => {
  try {
    const [statsRes, complexityRes, errorRes] = await Promise.all([
      getDashboardStats(),
      getComplexityAnalysis(),
      getErrorDistribution(),
    ])
    stats.value = statsRes.data
    complexity.value = complexityRes.data
    errorDist.value = errorRes.data.distribution
  } catch (error) {
    console.error('Failed to load dashboard data:', error)
  }
})
</script>

<style scoped>
.dashboard {
  /* padding: 20px;  已被 App.vue 统一管理 */
}

.stat-card {
  height: 120px;
}

.stat-card :deep(.el-card__body) {
  height: 100%;
  display: flex;
  align-items: center;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 20px;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #333;
}

.stat-label {
  font-size: 14px;
  color: #999;
  margin-top: 5px;
}

.chart-container {
  height: 250px;
}

.complexity-info {
  padding: 10px;
}

.complexity-item {
  display: flex;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid #eee;
}

.complexity-item:last-child {
  border-bottom: none;
}

.complexity-item .label {
  color: #666;
}

.complexity-item .value {
  font-weight: bold;
  color: #333;
}
</style>
