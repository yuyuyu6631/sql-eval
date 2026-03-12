<template>
  <div class="app-container">
    <el-container>
      <el-aside width="220px" class="sidebar">
        <div class="logo">
          <h2>SQL Eval</h2>
        </div>
        <el-menu
          :default-active="$route.path"
          router
          class="sidebar-menu"
        >
          <el-menu-item index="/">
            <el-icon><DataAnalysis /></el-icon>
            <span>{{ t('common.dashboard') }}</span>
          </el-menu-item>
          <el-menu-item index="/environments">
            <el-icon><Setting /></el-icon>
            <span>{{ t('common.environment') }}</span>
          </el-menu-item>
          <el-menu-item index="/test-cases">
            <el-icon><Document /></el-icon>
            <span>{{ t('common.testCases') }}</span>
          </el-menu-item>
          <el-menu-item index="/agents">
            <el-icon><User /></el-icon>
            <span>{{ t('common.agents') }}</span>
          </el-menu-item>
          <el-menu-item index="/tasks">
            <el-icon><Promotion /></el-icon>
            <span>{{ t('common.tasks') }}</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      <el-container>
        <el-header class="header">
          <div class="header-left">
            <h3>{{ pageTitle }}</h3>
          </div>
          <div class="header-right">
            <el-button type="primary" plain @click="toggleLocale">
              {{ locale === 'zh' ? 'English' : '中文' }}
            </el-button>
          </div>
        </el-header>
        <el-main class="main-content">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { DataAnalysis, Setting, Document, User, Promotion } from '@element-plus/icons-vue'
import { t, toggleLocale, locale } from './i18n'

const route = useRoute()

const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    '/': t('common.dashboard'),
    '/environments': t('env.title'),
    '/test-cases': t('testCase.title'),
    '/agents': t('agent.title'),
    '/tasks': t('task.title'),
  }
  return titles[route.path] || 'Text-to-SQL Evaluation'
})
</script>

<style scoped>
.app-container {
  height: 100vh;
  width: 100vw;
  overflow: hidden; /* 防止根容器出现滚动条 */
}

.el-container {
  height: 100%;
}

.sidebar {
  background-color: #304156;
  color: #fff;
  height: 100%;
  transition: width 0.3s;
  flex-shrink: 0; /* 禁止侧边栏被挤压 */
  border-right: 1px solid #1f2d3d;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid #404854;
}

.logo h2 {
  color: #409eff;
  margin: 0;
  font-size: 1.5rem;
}

.sidebar-menu {
  border-right: none;
  background-color: #304156;
}

.sidebar-menu .el-menu-item {
  color: #bfcbd9;
}

.sidebar-menu .el-menu-item:hover,
.sidebar-menu .el-menu-item.is-active {
  background-color: #263445;
  color: #409eff;
}

.header {
  background-color: #fff;
  border-bottom: 1px solid #e6e6e6;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 60px;
  flex-shrink: 0; /* Header 高度固定 */
}

.header-left h3 {
  margin: 0;
  color: #333;
}

.main-content {
  background-color: #f0f2f5;
  padding: 20px; /* 统一在该层级管理间距 */
  flex: 1;
  overflow-y: auto; /* 关键：仅内容区滚动 */
  height: calc(100vh - 60px);
}
</style>
