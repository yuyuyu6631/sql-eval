# 后端设计重点及前端输出需求 (Backend Design Focus - UI/UX Pro Max 版)

在遵循极致体验（UI/UX Pro Max）与高质量编码的大前提下，接手该系统的前端需产出以下特定模块的设计梳理。本部分为项目对接落地前最核心的验收点。

## 1. 必须优先提交及解决的设计重点

### 1.1 轮询进度的体验设计 (`loading-states`)
- 测评的执行和用例 AI 生成是典型的异步任务。
- **前端输出要求**:
  - 设计合理的轮询拉取 (Polling) 机制图或者包含 ProgressBar 增长状态的交互流呈现。
  - 当请求过程中，保证界面元素不可发生任何布局跳跃 (`layout shift`)，保证任务启动按钮有明显的防重复点击保护 (`Disabled 并且自带 Spinner`)。

### 1.2 高维度数据的代码/信息对比展示 (`readable-font-size` & `color-contrast`)
- 系统需要在评测结果中展示大段的 SQL、报错堆栈或 AI 诊断文本 (Result Diagnosis)。
- **前端输出要求**:
  - 对于带有高密度信息的展示组件方案，文字必须高于 **16px** 易读基准。
  - 如果使用代码高亮 (Syntax Highlighting) 或者对比组件 (Diff Component)，提交**多主题对比度审查**，确保在深浅模式 (Light/Dark mode) 的文本与背景对比度全部达标的预案。

### 1.3 核心图标与指示器梳理 (`no-emoji-icons`)
- **前端输出要求**:
  - 将所有状态流转 (TaskStatus: PENDING -> RUNNING -> COMPLETED) 使用的 Emoji 等待/报错表情废弃。
  - 输出准备引用的标准化矢量化图标集（推荐采用 SVG Heroicons 统一导入）。

## 2. 需输出的前端物料交付核对单 (Pre-Delivery UX Checklist)

在真正落码并交付之前，前端需回答以下梳理材料供团队评审：

- [ ] **交互行为文档 (Interaction Map)**: 含带明确跳转规则以及报错 404/500 的回退兜底（Fallback）路径。
- [ ] **核心类型映射声明 (TypeScript Declaration)**: 基于后端的现存返回体，罗列出所有的关键业务模型 `interface`。
- [ ] **视觉效果双端支持策略**: 对于主要图表或者关键操作（Dashboard, 任务执行等），明确其不同响应式断点（375px / 768px / 1200+px）时的行为，防止由于缩小导致的横向强制滚动缺陷。

通过对上述重点需求的高标准把控，我们将确保这个从文本到 SQL 的测评核心系统兼具强悍的功能与令人惊喜的工业级使用体验。
