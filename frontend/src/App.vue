<template>
  <div class="app-wrapper" :data-theme="isDark ? 'dark' : 'light'">
    <!-- 极简背景层 -->
    <div class="app-bg" aria-hidden="true">
      <div class="bg-glow bg-glow-1"></div>
      <div class="bg-glow bg-glow-2"></div>
    </div>

    <!-- 侧边栏（语义化 nav + aria）-->
    <aside
      class="sidebar"
      :class="{ 'is-collapsed': isCollapsed }"
      role="navigation"
      :aria-label="t('common.mainNav')"
    >
      <!-- Logo 区域 -->
      <div class="sidebar-header">
        <div class="logo" v-show="!isCollapsed">
          <!-- SVG 图标，避免使用 Emoji -->
          <div class="logo-icon" aria-hidden="true">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
            </svg>
          </div>
          <span class="logo-name">SQL <strong>EVAL</strong></span>
        </div>
        <div class="logo-icon-only" v-show="isCollapsed" aria-hidden="true">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
          </svg>
        </div>
      </div>

      <!-- 导航菜单 -->
      <nav class="nav-menu" role="menubar">
        <router-link
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          active-class="is-active"
          role="menuitem"
          :aria-label="item.label"
          :title="isCollapsed ? item.label : undefined"
        >
          <span class="nav-icon" aria-hidden="true" v-html="item.icon"></span>
          <span class="nav-label" v-show="!isCollapsed">{{ item.label }}</span>
        </router-link>
      </nav>

      <!-- 折叠按钮 -->
      <button
        class="collapse-btn"
        @click="isCollapsed = !isCollapsed"
        :aria-label="isCollapsed ? t('common.expandSidebar') : t('common.collapseSidebar')"
        :aria-expanded="!isCollapsed"
      >
        <span aria-hidden="true" v-html="isCollapsed ? ICON_EXPAND : ICON_COLLAPSE"></span>
      </button>

      <!-- 底部状态 -->
      <div class="sidebar-footer" v-show="!isCollapsed">
        <div class="sys-status">
          <span class="status-dot" aria-hidden="true"></span>
          <span>{{ t('common.systemActive') }}</span>
        </div>
      </div>
    </aside>

    <!-- 主内容区 -->
    <main class="main-area">
      <!-- 顶部 Header -->
      <header class="app-header" role="banner">
        <div class="header-left">
          <span class="page-breadcrumb" aria-label="current page">{{ pageTitle }}</span>
        </div>

        <div class="header-right">
          <!-- 主题切换 -->
          <button
            class="icon-btn"
            @click="toggleTheme"
            :aria-label="isDark ? t('common.switchLight') : t('common.switchDark')"
            :title="isDark ? t('common.switchLight') : t('common.switchDark')"
          >
            <span aria-hidden="true" v-html="isDark ? ICON_SUN : ICON_MOON"></span>
          </button>

          <!-- 语言切换 -->
          <button
            class="lang-btn"
            @click="toggleLanguage"
            :aria-label="`Switch to ${currentLang === 'zh' ? 'English' : '中文'}`"
          >
            {{ currentLang === 'zh' ? 'EN' : 'ZH' }}
          </button>

          <div class="header-divider" aria-hidden="true"></div>

          <!-- 用户头像 -->
          <div class="user-avatar" role="img" aria-label="user avatar">
            <img
              src="https://api.dicebear.com/7.x/avataaars/svg?seed=sqleval"
              alt="User avatar"
              loading="lazy"
            />
          </div>
        </div>
      </header>

      <!-- 页面内容 -->
      <div class="page-body">
        <router-view v-slot="{ Component, route }">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" :key="route.fullPath" />
          </transition>
        </router-view>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { t, toggleLocale, locale } from './i18n'

/* ---- SVG 图标常量（避免使用 Emoji）---- */
const ICON_DASHBOARD = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/></svg>`
const ICON_ENV      = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>`
const ICON_CASE     = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>`
const ICON_AGENT    = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"/></svg>`
const ICON_TASK     = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>`
const ICON_SUN      = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>`
const ICON_MOON     = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>`
const ICON_EXPAND   = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="13 17 18 12 13 7"/><polyline points="6 17 11 12 6 7"/></svg>`
const ICON_COLLAPSE = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="11 17 6 12 11 7"/><polyline points="18 17 13 12 18 7"/></svg>`

/* ---- 导航定义 ---- */
const navItems = computed(() => [
  { to: '/',             label: t('common.dashboard'),  icon: ICON_DASHBOARD },
  { to: '/environments', label: t('env.title'),          icon: ICON_ENV },
  { to: '/test-cases',   label: t('testCase.title'),     icon: ICON_CASE },
  { to: '/agents',       label: t('agent.title'),        icon: ICON_AGENT },
  { to: '/tasks',        label: t('task.title'),         icon: ICON_TASK },
])

/* ---- 侧边栏折叠 ---- */
const isCollapsed = ref(localStorage.getItem('sidebar-collapsed') === 'true')
watch(isCollapsed, val => localStorage.setItem('sidebar-collapsed', String(val)))

/* ---- 主题 ---- */
const isDark = ref(localStorage.getItem('app-theme') !== 'light')

const applyTheme = () => {
  document.documentElement.setAttribute('data-theme', isDark.value ? 'dark' : 'light')
}

const toggleTheme = () => {
  isDark.value = !isDark.value
  localStorage.setItem('app-theme', isDark.value ? 'dark' : 'light')
  applyTheme()
}

onMounted(applyTheme)

/* ---- 语言 ---- */
const currentLang = locale
const toggleLanguage = toggleLocale

/* ---- 页面标题 ---- */
const route = useRoute()
const pageTitle = computed(() => {
  const map: Record<string, string> = {
    '/':             t('common.dashboard'),
    '/environments': t('env.title'),
    '/test-cases':   t('testCase.title'),
    '/agents':       t('agent.title'),
    '/tasks':        t('task.title'),
  }
  return map[route.path] || 'Platform'
})
</script>

<style>
@import './styles/main.css';
@import './styles/components.css';

.app-wrapper {
  display: flex;
  height: 100vh;
  width: 100vw;
  background-color: var(--m-bg);
  color: var(--m-text);
  overflow: hidden;
  font-family: var(--font-ui);
  transition: background-color var(--t-normal), color var(--t-normal);
}
</style>

<style scoped>
/* ---- 背景装饰层 ---- */
.app-bg {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}

.bg-glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.03;
}

[data-theme="dark"] .bg-glow-1 {
  width: 400px;
  height: 400px;
  background: var(--m-primary);
  top: -100px;
  left: -100px;
}

[data-theme="dark"] .bg-glow-2 {
  width: 300px;
  height: 300px;
  background: var(--m-accent);
  bottom: -80px;
  right: -80px;
}

/* ---- 侧边栏 ---- */
.sidebar {
  width: var(--m-sb-w);
  height: 100vh;
  background: transparent;
  border-right: 1px solid var(--m-border);
  display: flex;
  flex-direction: column;
  z-index: var(--z-base);
  transition: width var(--t-slow);
  position: relative;
  flex-shrink: 0;
}

.sidebar.is-collapsed {
  width: var(--m-sb-w-c);
}

.sidebar-header {
  height: var(--m-header-h);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 16px;
  border-bottom: 1px solid var(--m-border);
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  overflow: hidden;
}

.logo-icon {
  width: 30px;
  height: 30px;
  background: var(--m-primary);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #000;
  flex-shrink: 0;
}

.logo-icon-only {
  width: 30px;
  height: 30px;
  background: var(--m-primary);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #000;
}

.logo-name {
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.5px;
  white-space: nowrap;
  color: var(--m-text);
}

.logo-name strong {
  color: var(--m-primary);
}

/* ---- 导航菜单 ---- */
.nav-menu {
  flex: 1;
  padding: 12px 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 40px;
  padding: 0 12px;
  border-radius: var(--radius-lg);
  color: var(--m-text-muted);
  text-decoration: none;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  /* ✅ 正确：transition-colors，不 transform */
  transition: background-color var(--t-fast), color var(--t-fast);
  white-space: nowrap;
  overflow: hidden;
  position: relative;
}

.nav-item:hover {
  background: var(--m-surface-bright);
  color: var(--m-text);
}

.nav-item.is-active {
  background: var(--m-primary-ghost);
  color: var(--m-primary);
  font-weight: 600;
}

.nav-item.is-active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 3px;
  background: var(--m-primary);
  border-radius: 0 3px 3px 0;
}

.nav-icon {
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.nav-label {
  transition: opacity var(--t-fast);
}

/* ---- 折叠按钮 ---- */
.collapse-btn {
  margin: 8px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid var(--m-border);
  border-radius: var(--radius-md);
  color: var(--m-text-muted);
  cursor: pointer;
  transition: background-color var(--t-fast), color var(--t-fast), border-color var(--t-fast);
}

.collapse-btn:hover {
  background: var(--m-surface-bright);
  color: var(--m-text);
  border-color: var(--m-border-strong);
}

/* ---- 侧边栏底部 ---- */
.sidebar-footer {
  padding: 12px 16px;
  border-top: 1px solid var(--m-border);
}

.sys-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: var(--m-text-muted);
}

.status-dot {
  width: 6px;
  height: 6px;
  background: var(--m-primary);
  border-radius: 50%;
  box-shadow: 0 0 6px var(--m-primary);
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

@media (prefers-reduced-motion: reduce) {
  .status-dot { animation: none; }
}

/* ---- 主内容区 ---- */
.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  z-index: var(--z-base);
  min-width: 0;
}

/* ---- 顶部 Header ---- */
.app-header {
  height: var(--m-header-h);
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--m-border);
  background: rgba(9, 9, 11, 0.6);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  flex-shrink: 0;
}

[data-theme="light"] .app-header {
  background: rgba(255, 255, 255, 0.8);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-breadcrumb {
  font-size: 14px;
  font-weight: 600;
  color: var(--m-text);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* ✅ 图标按钮：有 cursor-pointer，有 hover 反馈，无 transform */
.icon-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  color: var(--m-text-muted);
  cursor: pointer;
  transition: background-color var(--t-fast), color var(--t-fast);
}

.icon-btn:hover {
  background: var(--m-surface-bright);
  color: var(--m-text);
}

.lang-btn {
  height: 36px;
  padding: 0 10px;
  background: transparent;
  border: 1px solid var(--m-border);
  border-radius: var(--radius-md);
  color: var(--m-text-muted);
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  font-family: var(--font-ui);
  transition: background-color var(--t-fast), color var(--t-fast), border-color var(--t-fast);
}

.lang-btn:hover {
  background: var(--m-surface-bright);
  color: var(--m-text);
  border-color: var(--m-border-strong);
}

.header-divider {
  width: 1px;
  height: 20px;
  background: var(--m-border);
  margin: 0 4px;
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1px solid var(--m-border);
  overflow: hidden;
  background: var(--m-surface-bright);
  cursor: pointer;
  transition: border-color var(--t-fast);
}

.user-avatar:hover {
  border-color: var(--m-border-strong);
}

.user-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

/* ---- 页面内容 ---- */
.page-body {
  flex: 1;
  overflow-y: auto;
  padding: 28px 32px;
}

/* ---- 页面切换动画（ease-out 进入，ease-in 退出）---- */
.page-fade-enter-from {
  opacity: 0;
}

.page-fade-enter-active {
  transition: opacity 200ms ease-out;
}

.page-fade-leave-to {
  opacity: 0;
}

.page-fade-leave-active {
  transition: opacity 150ms ease-in;
}
</style>
