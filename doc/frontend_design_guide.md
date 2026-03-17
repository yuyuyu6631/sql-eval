# 前端设计指南 (Frontend Design Guide - UI/UX Pro Max 版)

本设计指南严格遵循 **UI/UX Pro Max** 规范，致力于在系统的前端建设中落地极致的用户体验、无障碍访问 (Accessibility) 和高性能标准。

## 1. 核心优先级约束 (Priority Categories)
前端开发所有决策必须按照以下优先级进行考量：
1. **Accessibility (CRITICAL)**: 无障碍访问优先。
2. **Touch & Interaction (CRITICAL)**: 交互点击和触摸响应。
3. **Performance (HIGH)**: 性能与流畅度优化。
4. **Layout & Responsive (HIGH)**: 响应式布局。
5. **Typography & Color (MEDIUM)**: 排版与颜色。
6. **Animation (MEDIUM)**: 动画和微交互。

## 2. 无障碍与可访问性 (Accessibility)
- **色差对比度 (`color-contrast`)**: 正常文本的对比度必须 **≥ 4.5:1**，禁用低对比度的浅灰色（如光亮模式下不要用 `#94A3B8(slate-400)` 作为正文，需用 `#0F172A(slate-900)`）。
- **焦点状态 (`focus-states`)**: 所有交互元素必须保留可见的焦点环 (Focus Rings)，方便键盘导航。
- **键盘导航 (`keyboard-nav`)**: 确保 Tab 键的焦点移动顺序与视觉元素的展示顺序完全一致。
- **语义化标签 (`aria-labels` & `alt-text`)**: 纯图标按钮必须加 `aria-label`；有意义的图片必须包含描述性 `alt` 文本。

## 3. 交互与触摸响应 (Touch & Interaction)
- **触摸目标尺寸 (`touch-target-size`)**: 所有的可点击目标（按钮、图标）在移动端或触控设备上必须达到 **44x44px** 及以上。
- **指针与悬停反馈 (`cursor-pointer` & `hover-feedback`)**:
  - 所有可点击或可悬停的卡片、元素必须带有 `cursor-pointer`。
  - 需要清晰的 Hover 视觉反馈（通过颜色、阴影或边框实现），但**绝对不可以导致布局偏移 (layout shift)**。禁止在 Hover 时使用强烈的宽高、缩放变化。
- **异步操作保护 (`loading-buttons`)**:
  - 表单提交或者发网络请求时，务必将按钮状态置为 Disabled 并展示 Loading 状态。
- **平滑过渡 (`smooth-transitions`)**: 状态切换过渡时间需控制在 **150-300ms**，并在 Tailwind 中使用 `transition-colors duration-200` 等进行控制。

## 4. 视觉与排版规范 (Visual Quality & Typography)
- **纯正的图标资产**: 
  - 禁止使用系统 Emoji 符号（如 🎨 🚀 ⚙️）作为正式 UI 图标。
  - 必须使用标准的 SVG 图标集（如 Heroicons, Lucide, Simple Icons），且保持一致的视口基准（如 `viewBox="0 0 24 24"` 并使用 `w-6 h-6` 控制）。
- **字体与行高**:
  - 正文排版阅读行高保持在 **1.5 - 1.75**，每行中文字符控制在 **65 - 75** 字左右。
- **暗黑/明亮双主题 (Light/Dark Mode)**:
  - 凡是使用 Glassmorphism (毛玻璃) 效果，在 Light Mode 必须用至少 `bg-white/80` 来保证可见度（禁止用 `bg-white/10` 导致透明不可见）。
  - 边框在深浅模式下都必须保持清晰可见。

## 5. 布局与响应式 (Layout & Responsive)
- **移动优先与层级管理 (`z-index-management`)**: 建立并严格遵守清晰的 Z-Index 刻度体系（例如 10, 20, 30, 50，避免随意出现 9999）。
- **防止内容跳动 (`content-jumping`)**: 对于异步加载的内容区块（如图表、数据表格），需预先占位 (Skeleton Screen 或固定比例盒子)。
- **一致的最大宽度**: 使用全局统一的容器（例如 `max-w-6xl` 或 `max-w-7xl`）进行内聚包裹，防止不同页面内容区域宽度跳变。
- **移动端优化**: 禁止移动端出现引起横向滚动的越界元素。

## 6. 技术栈建议 (HTML-Tailwind Default / React / Vue)
- **性能红线**: 使用 WebP 格式图片，启用懒加载，对复杂的交互组件通过懒加载/分包避免打包体积过大。
- 考虑到复杂性较低的操作应采用 CSS Transform / Opacity 来做动画，**坚决不要用引发重绘的 width/height 动画**。
