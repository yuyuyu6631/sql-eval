# SQL-EVAL 项目专用 Skill 流（测试体系）

## 1. 目标
- 建立一套可重复执行的“技能驱动测试体系”
- 保证项目在每次改动后都能达到“可启动、可访问、可评测、可连通”

## 2. Skill 组合（固定）
1. `Code`：拆解测试任务与回归范围
2. `test-runner`：执行自动化测试与冒烟命令
3. `debug-pro`：定位失败根因并给出修复路径
4. `find-skills`：当出现能力缺口时补充新测试技能

## 3. 流程主干（每次改动都走）

### Step A：制定本次测试范围（Code）
- 输入：本次改动文件、影响模块
- 输出：本轮测试清单（最少覆盖启动、核心 API、评测链路）

准入标准：
- 明确“必须通过项”和“可延期项”

### Step B：自动化回归（test-runner）
执行：
```bash
backend/.runtime-venv/Scripts/python.exe -m pytest -q
```

通过标准：
- `pytest` 无失败（允许非阻塞 warning）

### Step C：启动冒烟（test-runner）
执行：
```bash
python start.py --skip-install --smoke-seconds 15
```

通过标准：
- 前后端都能拉起
- 健康检查可用
- 进程可自动退出

### Step D：核心 API 冒烟（test-runner）
最小必测接口：
- `GET /health`
- `GET /api/agents`
- `GET /api/tasks`
- `GET /api/system/judge-config`
- `POST /api/system/judge-config/test`（有 key 时）

通过标准：
- 核心接口返回 200 或可读业务错误（非 500）

### Step E：失败闭环（debug-pro）
- 发生失败时必须输出：
1. 失败接口/用例
2. 复现命令
3. 根因定位
4. 修复建议与优先级（P0/P1/P2）

## 4. 能力缺口补齐（find-skills）
触发条件：
- 需要 UI 自动化、性能压测、契约测试但当前技能不足

检索命令示例：
```bash
npx skills find "fastapi testing"
npx skills find "playwright e2e"
npx skills find "api contract testing"
```

新增 skill 进入体系规则：
- 先小范围试用（单模块）
- 再纳入主流程
- 写入本文档“固定组合”

## 5. 项目级 DoD（可交付标准）
- 自动化测试：通过
- 启动烟测：通过
- 核心 API 冒烟：通过
- 裁判模型连通测试：可用或有明确错误提示
- 生成测试报告：`test/TEST_REPORT.md`

## 6. 执行节奏建议
- 每次功能改动：执行 Step A~E
- 每天收工前：至少跑一次 Step B + Step C
- 发布前：完整执行 Step B~E 并更新测试报告

