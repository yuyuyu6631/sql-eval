# SQL-EVAL 测试计划（Skill 驱动）

## 1. 目标
- 确保系统可启动、核心页面可打开、核心 API 可用、评测流程可执行。
- 验证裁判模型配置与连通测试链路稳定。
- 为后续回归提供统一执行清单。

## 2. Skill 调用约定
- 计划与拆解：`Code` skill
- 测试执行与验证：`test-runner` skill
- 故障定位（失败时）：`debug-pro` skill

## 3. 测试范围
- 后端：FastAPI 路由、评测服务、沙箱执行、裁判模型连通测试接口
- 前端：`Dashboard / 环境配置 / 测试用例管理 / 评测任务列表 / 智能体配置`
- 启动链路：`python start.py`
- 配置链路：`.env + backend/.secrets/judge_api_key`

## 4. 执行前准备
- Python 使用项目运行时虚拟环境：`backend/.runtime-venv`
- 安装依赖：
```bash
backend/.runtime-venv/Scripts/python.exe -m pip install -r backend/requirements-dev.txt
```
- 启动系统：
```bash
python start.py
```
- 健康检查：
```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:5173
```

## 5. 用例清单

### A. 单元/服务测试（test-runner）
1. 评测重试逻辑：`backend/app/services/test_evaluator_retry.py`
2. 并发评测逻辑：`backend/app/services/test_evaluator_concurrency.py`
3. Real DB 沙箱路由：`backend/app/services/test_sandbox_real_db.py`

执行命令：
```bash
backend/.runtime-venv/Scripts/python.exe -m pytest -q
```

通过标准：
- 全部测试通过（当前基线 6 passed）。

### B. API 集成测试（Code + test-runner）
1. 获取裁判配置：`GET /api/system/judge-config`
2. 更新裁判配置：`PUT /api/system/judge-config`
3. 连通测试：`POST /api/system/judge-config/test`
4. 任务创建与查询：`POST /api/tasks` + `GET /api/tasks`

通过标准：
- 200/业务成功返回，错误场景返回可读错误（非 500）。

### C. 前端冒烟测试（Code）
1. 左侧菜单 5 个核心页面均可打开，无白屏
2. 页面主内容区域样式一致（无大面积异常色块）
3. 裁判模型配置保存后刷新仍可读取

通过标准：
- 所有页面可渲染，接口失败时有可见提示。

### D. 启动与依赖回归（Code + debug-pro）
1. `python start.py` 首次安装依赖后可完成启动
2. 二次启动可复用已有环境，且不报关键错误
3. 端口冲突时有明确报错信息

通过标准：
- 启动稳定，不出现“卡住无输出”问题。

## 6. 缺陷分级与处理
- P0：无法启动、关键页面打不开、任务执行链路断裂
- P1：连通测试失败但主流程可用、关键功能报错
- P2：UI 显示偏差、非关键日志告警

## 7. 交付物
- 测试结果记录：`test/TEST_REPORT.md`（建议新增）
- 失败日志：`backend/server.log`、`frontend/frontend.log`
- 回归命令记录：保存在 PR 描述或 issue 中

