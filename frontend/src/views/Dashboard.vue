<template>
  <div class="dashboard">
    <!-- KPI 核心指标 -->
    <div class="kpi-row">
      <!-- 骨架屏：加载中 -->
      <template v-if="isLoading">
        <div v-for="i in 4" :key="i" class="m-skeleton kpi-card" style="height: 110px;"></div>
      </template>
      <!-- 数据加载完成 -->
      <template v-else>
        <div class="kpi-card">
          <div class="kpi-label">{{ t('dashboard.totalTasks') }}</div>
          <div class="kpi-value">{{ stats.total_tasks ?? 0 }}</div>
          <div class="kpi-sub">{{ t('dashboard.allTime') }}</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">{{ t('dashboard.testCases') }}</div>
          <div class="kpi-value">{{ stats.total_cases ?? 0 }}</div>
          <div class="kpi-sub">{{ t('dashboard.activeNow') }}</div>
        </div>
        <div class="kpi-card accent-card">
          <div class="kpi-label">{{ t('dashboard.passRate') }}</div>
          <div class="kpi-value accent">{{ stats.pass_rate ?? 0 }}<small>%</small></div>
          <div class="kpi-progress-bar">
            <div class="kpi-progress-fill" :style="{ width: (stats.pass_rate ?? 0) + '%' }"></div>
          </div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">{{ t('dashboard.results') }}</div>
          <div class="kpi-value">{{ stats.total_results ?? 0 }}</div>
          <div class="kpi-sub">{{ t('dashboard.evaluations') }}</div>
        </div>
      </template>
    </div>

    <!-- 图表行 -->
    <div class="charts-row">
      <!-- 任务状态分布（Donut）-->
      <div class="m-card chart-card">
        <div class="card-header">
          <h2 class="card-title">{{ t('dashboard.statusDistribution') }}</h2>
          <span class="card-sub">{{ t('dashboard.taskHealth') }}</span>
        </div>
        <div v-if="isLoading" class="m-skeleton" style="height: 200px; border-radius: 8px;"></div>
        <div v-else class="donut-wrap">
          <div class="donut-chart-area">
            <Pie :data="pieData" :options="donutOptions" />
          </div>
          <div class="donut-center-overlay">
            <div class="donut-val">{{ stats.total_tasks ?? 0 }}</div>
            <div class="donut-hint">{{ t('dashboard.tasks') }}</div>
          </div>
          <!-- 图例（Pie 无障碍改进：加文字图例）-->
          <div class="donut-legend" role="list" :aria-label="t('dashboard.statusLegend')">
            <div
              v-for="(count, status) in stats.status_counts"
              :key="status"
              class="legend-item"
              role="listitem"
            >
              <span class="legend-dot" :style="{ background: statusColor(String(status)) }" aria-hidden="true"></span>
              <span class="legend-label">{{ status }}</span>
              <span class="legend-val">{{ count }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 错误分布（Horizontal Bar）-->
      <div class="m-card chart-card">
        <div class="card-header">
          <h2 class="card-title">{{ t('dashboard.errorDistribution') }}</h2>
          <span class="card-sub">{{ t('dashboard.failureRootCauses') }}</span>
        </div>
        <div v-if="isLoading" class="m-skeleton" style="height: 200px; border-radius: 8px;"></div>
        <div v-else-if="hasErrors" class="bar-list" role="list">
          <div
            v-for="(count, type) in sortedErrors"
            :key="type"
            class="bar-item"
            role="listitem"
            :aria-label="`${type}: ${count}`"
          >
            <div class="bar-label">{{ type }}</div>
            <div class="bar-track" role="progressbar" :aria-valuenow="Number(count)" :aria-valuemax="errorTotal">
              <div
                class="bar-fill"
                :style="{ width: errorPct(Number(count)) + '%', background: errorColor(String(type)) }"
              ></div>
            </div>
            <div class="bar-count font-mono">{{ count }}</div>
          </div>
        </div>
        <div v-else class="m-empty">
          <div class="m-empty-icon" aria-hidden="true">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
          </div>
          <div class="m-empty-title">{{ t('dashboard.noErrors') }}</div>
        </div>
      </div>
    </div>

    <!-- 性能指标 + 排行榜 -->
    <div class="bottom-row">
      <!-- 性能指标 -->
      <div class="m-card perf-card">
        <div class="card-header">
          <h2 class="card-title">{{ t('dashboard.complexityAnalysis') }}</h2>
        </div>
        <div v-if="isLoading" class="m-skeleton" style="height: 80px; border-radius:8px;"></div>
        <div v-else class="perf-grid">
          <div class="perf-item">
            <div class="perf-label">{{ t('dashboard.avgExecutionTime') }}</div>
            <div class="perf-val font-mono">{{ complexity.avg_execution_time_ms ?? 0 }}<small>ms</small></div>
          </div>
          <div class="perf-item danger">
            <div class="perf-label">{{ t('dashboard.slowestQuery') }}</div>
            <div class="perf-val font-mono">{{ complexity.slowest_query_ms ?? 0 }}<small>ms</small></div>
          </div>
          <div class="perf-item success">
            <div class="perf-label">{{ t('dashboard.fastestQuery') }}</div>
            <div class="perf-val font-mono">{{ complexity.fastest_query_ms ?? 0 }}<small>ms</small></div>
          </div>
          <div class="perf-item">
            <div class="perf-label">{{ t('dashboard.totalQueries') }}</div>
            <div class="perf-val font-mono">{{ complexity.total_queries ?? 0 }}</div>
          </div>
        </div>
      </div>

      <!-- Agent 排行榜 -->
      <div class="m-card leaderboard-card">
        <div class="card-header">
          <h2 class="card-title">{{ t('dashboard.leaderboard') }}</h2>
          <span class="card-sub">{{ t('dashboard.byPassRate') }}</span>
        </div>
        <div v-if="isLoading" class="m-skeleton" style="height: 120px; border-radius: 8px;"></div>
        <div v-else-if="leaderboard.length > 0" class="lb-list" role="list">
          <div
            v-for="(item, idx) in leaderboard"
            :key="item.agent_id"
            class="lb-item"
            role="listitem"
          >
            <div class="lb-rank" :class="{ 'rank-gold': idx === 0, 'rank-silver': idx === 1, 'rank-bronze': idx === 2 }">
              {{ idx + 1 }}
            </div>
            <div class="lb-info">
              <div class="lb-agent">Agent #{{ item.agent_id }}</div>
              <div class="lb-stats">{{ item.total_tests }} {{ t('dashboard.tests') }} · {{ item.passed }} {{ t('dashboard.passed') }}</div>
            </div>
            <div class="lb-rate" :class="{ 'rate-high': item.pass_rate >= 80, 'rate-low': item.pass_rate < 50 }">
              {{ item.pass_rate }}<small>%</small>
            </div>
          </div>
        </div>
        <div v-else class="m-empty">
          <div class="m-empty-icon" aria-hidden="true">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
          </div>
          <div class="m-empty-title">{{ t('dashboard.noAgentData') }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Pie } from 'vue-chartjs'
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js'
import type { DashboardStats, ComplexityAnalysis, LeaderboardItem } from '../types'
import { getDashboardStats, getComplexityAnalysis, getErrorDistribution, getLeaderboard } from '../api'
import { t } from '../i18n'

ChartJS.register(ArcElement, Tooltip, Legend)

/* ---- 状态 ---- */
const isLoading = ref(true)
const stats      = ref<DashboardStats>({ total_tasks: 0, total_cases: 0, total_results: 0, status_counts: {}, pass_rate: 0 })
const complexity = ref<ComplexityAnalysis>({ avg_execution_time_ms: 0, slowest_query_ms: 0, fastest_query_ms: 0, total_queries: 0 })
const errorDist  = ref<Record<string, number>>({})
const leaderboard = ref<LeaderboardItem[]>([])

/* ---- 图表配置 ---- */
const STATUS_COLORS: Record<string, string> = {
  completed: '#10b981',
  running:   '#3b82f6',
  pending:   '#f59e0b',
  failed:    '#ef4444',
}

const statusColor = (s: string) => STATUS_COLORS[s] ?? '#71717a'

const pieData = computed(() => ({
  labels: Object.keys(stats.value.status_counts ?? {}),
  datasets: [{
    data: Object.values(stats.value.status_counts ?? {}).map(Number),
    backgroundColor: Object.keys(stats.value.status_counts ?? {}).map(statusColor),
    borderWidth: 0,
    hoverOffset: 0,
  }],
}))

const donutOptions = {
  responsive: true,
  maintainAspectRatio: false,
  cutout: '80%',
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: '#18181b',
      titleFont: { size: 12, family: 'Inter' },
      bodyFont: { size: 12, family: 'Inter' },
      padding: 10,
      cornerRadius: 6,
      borderWidth: 1,
      borderColor: 'rgba(255,255,255,0.1)',
    },
  },
}

/* ---- 错误分布计算 ---- */
const sortedErrors = computed(() => {
  return Object.fromEntries(
    Object.entries(errorDist.value).sort(([, a], [, b]) => Number(b) - Number(a))
  )
})

const errorTotal = computed(() =>
  Object.values(errorDist.value).reduce((s, v) => s + Number(v), 0)
)

const hasErrors = computed(() => errorTotal.value > 0)

const errorPct = (count: number) =>
  errorTotal.value > 0 ? (count / errorTotal.value) * 100 : 0

const errorColor = (type: string) => {
  const map: Record<string, string> = {
    execution_error: '#ef4444',
    golden_error:    '#6366f1',
    syntax_error:    '#f59e0b',
    completed:       '#10b981',
  }
  return map[type] ?? '#71717a'
}

/* ---- 数据加载 ---- */
onMounted(async () => {
  try {
    const [s, c, e, lb] = await Promise.all([
      getDashboardStats(),
      getComplexityAnalysis(),
      getErrorDistribution(),
      getLeaderboard(),
    ])
    stats.value      = s.data
    complexity.value = c.data
    errorDist.value  = e.data.distribution ?? {}
    leaderboard.value = lb.data.leaderboard ?? []
  } catch (err) {
    console.error('[Dashboard] 加载数据失败:', err)
  } finally {
    isLoading.value = false
  }
})
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 20px;
  animation: fade-in 200ms ease-out;
}

@keyframes fade-in {
  from { opacity: 0; }
  to   { opacity: 1; }
}

/* ---- KPI 行 ---- */
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.kpi-card {
  background: var(--m-surface);
  border: 1px solid var(--m-border);
  border-radius: var(--radius-xl);
  padding: 20px 24px;
  transition: box-shadow var(--t-normal), border-color var(--t-normal);
}

/* ✅ 正确：box-shadow，不 transform */
.kpi-card:hover {
  border-color: var(--m-border-strong);
  box-shadow: var(--m-shadow-md);
}

.kpi-card.accent-card {
  border-color: rgba(16, 185, 129, 0.2);
  background: rgba(16, 185, 129, 0.04);
}

.kpi-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: var(--m-text-muted);
  margin-bottom: 10px;
}

.kpi-value {
  font-size: 32px;
  font-weight: 700;
  font-family: var(--font-mono);
  letter-spacing: -1.5px;
  line-height: 1;
  color: var(--m-text);
}

.kpi-value.accent {
  color: var(--m-primary);
}

.kpi-value small {
  font-size: 16px;
  font-weight: 500;
  opacity: 0.7;
  margin-left: 2px;
}

.kpi-sub {
  margin-top: 8px;
  font-size: 11px;
  color: var(--m-text-dim);
}

.kpi-progress-bar {
  margin-top: 12px;
  height: 3px;
  background: rgba(16, 185, 129, 0.15);
  border-radius: 2px;
  overflow: hidden;
}

.kpi-progress-fill {
  height: 100%;
  background: var(--m-primary);
  border-radius: 2px;
  transition: width 1s cubic-bezier(0.4, 0, 0.2, 1);
}

/* ---- 图表行 ---- */
.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.chart-card {
  padding: 24px;
}

.card-header {
  margin-bottom: 20px;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--m-text);
  margin: 0;
}

.card-sub {
  display: block;
  font-size: 12px;
  color: var(--m-text-muted);
  margin-top: 3px;
}

/* Donut 图 */
.donut-wrap {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.donut-chart-area {
  height: 180px;
  position: relative;
}

.donut-center-overlay {
  /* 注：CSS 无法在 canvas 上叠加，通过绝对定位实现 */
  display: none; /* Chart.js 本身带 cutout，用 Legend 替代 */
}

.donut-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.legend-label {
  color: var(--m-text-muted);
}

.legend-val {
  font-family: var(--font-mono);
  font-weight: 600;
  color: var(--m-text);
}

/* 水平条形图 */
.bar-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.bar-item {
  display: grid;
  grid-template-columns: 120px 1fr 44px;
  align-items: center;
  gap: 12px;
}

.bar-label {
  font-size: 12px;
  color: var(--m-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bar-track {
  height: 6px;
  background: var(--m-surface-bright);
  border-radius: 3px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
}

.bar-count {
  font-size: 12px;
  font-weight: 600;
  text-align: right;
  color: var(--m-text);
}

/* ---- 底部行 ---- */
.bottom-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

/* 性能指标 */
.perf-card {
  padding: 24px;
}

.perf-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.perf-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.perf-label {
  font-size: 11px;
  color: var(--m-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.perf-val {
  font-size: 22px;
  font-weight: 700;
  color: var(--m-text);
}

.perf-val small {
  font-size: 11px;
  opacity: 0.5;
  margin-left: 2px;
}

.perf-item.danger .perf-val { color: var(--m-danger); }
.perf-item.success .perf-val { color: var(--m-primary); }

/* 排行榜 */
.leaderboard-card {
  padding: 24px;
}

.lb-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.lb-item {
  display: grid;
  grid-template-columns: 28px 1fr auto;
  align-items: center;
  gap: 12px;
  padding: 10px;
  border-radius: var(--radius-md);
  transition: background-color var(--t-fast);
}

.lb-item:hover {
  background: var(--m-surface-hover);
}

.lb-rank {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  background: var(--m-surface-bright);
  color: var(--m-text-muted);
}

.lb-rank.rank-gold   { background: rgba(234, 179, 8, 0.2);  color: #eab308; }
.lb-rank.rank-silver { background: rgba(148, 163, 184, 0.2); color: #94a3b8; }
.lb-rank.rank-bronze { background: rgba(180, 120, 60, 0.2);  color: #b4783c; }

.lb-agent {
  font-size: 13px;
  font-weight: 600;
  color: var(--m-text);
}

.lb-stats {
  font-size: 11px;
  color: var(--m-text-muted);
  margin-top: 2px;
}

.lb-rate {
  font-size: 16px;
  font-weight: 700;
  font-family: var(--font-mono);
  color: var(--m-text);
}

.lb-rate small {
  font-size: 11px;
  opacity: 0.6;
}

.lb-rate.rate-high { color: var(--m-primary); }
.lb-rate.rate-low  { color: var(--m-danger); }

/* 工具类 */
.font-mono { font-family: var(--font-mono); }
</style>
