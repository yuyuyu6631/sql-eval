# SQL-EVAL 初步可用性测试报告

## 1. 技能检索结果（find-skills）
通过 `npx skills find` 检索到测试相关候选：
- `eyadsibai/ltk@fastapi-testing`
- `hieutrtr/ai1-skills@pytest-patterns`
- `bobmatnyc/claude-mpm-skills@playwright-e2e-testing`

本次优先采用当前已安装且最贴合项目的技能执行测试：
- `test-runner`：执行自动化测试与冒烟命令
- `debug-pro`：定位失败与告警风险点

## 2. 已执行测试

### A. 后端核心 API 冒烟（ASGI 内测）
测试端点：
- `GET /health`
- `GET /api/dashboard/stats`
- `GET /api/agents`
- `GET /api/tasks`
- `GET /api/system/judge-config`

结果：全部 `200`

### A2. 业务主流程端到端冒烟（真实评测链路）
执行链路：
1. `POST /api/schema-envs` 创建测试环境
2. `POST /api/agents` 创建 `mock` 智能体
3. `POST /api/test-cases` 创建用例
4. `POST /api/tasks` 创建任务
5. `POST /api/tasks/{id}/start` 启动任务
6. `GET /api/tasks/{id}/progress` 轮询进度
7. `GET /api/results?task_id={id}` 校验结果

本轮结果（2026-03-17）：
- 创建环境/智能体/用例/任务全部 `201`
- 启动任务 `200`
- 任务状态：`completed`
- 任务统计：`passed=1, failed=0, errors=0`
- 结果条目：`1`
- `execution_status=completed`，`data_diff_passed=true`

### B. 自动化测试
命令：
```bash
backend/.runtime-venv/Scripts/python.exe -m pytest -q
```
结果：
- `6 passed`
- 有 warnings（不阻塞通过）

### C. 启动链路烟测
命令：
```bash
python start.py --skip-install --smoke-seconds 12
```
结果：
- 前后端均成功启动
- 健康检查通过
- 自动停止正常

## 3. 初步可用性结论
- 结论：项目已达到“初步可使用”状态。
- 核心后端接口可用，测试链路可执行，启动脚本可完成起停。

## 4. 当前已知非阻塞问题
- `pytest` 存在若干 `PytestCollectionWarning`（命名冲突类被识别为测试类）
- 运行结束有 `coroutine 'connect' was never awaited` 的运行时告警
- `start.py` 在前端端口被占用时，控制台展示的 Frontend URL 仍显示 `5173`，与实际端口（如 `5177`）不一致

## 5. 建议下一步
- 修正 `start.py` 的前端实际端口识别与输出
- 处理 `asyncpg connect` 的未 await 告警
- 清理 pytest 收集告警，保证回归输出更干净
