# Text-to-SQL 自动化测试平台 - 系统架构与设计方案 (基于最终版 PRD)

基于您更新的“沙箱双跑 + 结果集比对，高阶大模型兜底诊断”这一核心思路，重构了系统架构与数据库结构草案。

## 一、 系统架构更新

新的架构更加强调**沙箱执行的绝对重要性**以及**安全性**：
1. **Frontend (前端)**: Vue3 / React。重点实现：核心 Dashboard（大模型诊断错因分布）、左右分屏的 Diff UI（SQL Diff 与 Data Diff 高亮对比）。
2. **Backend (后端)**: FastAPI / Spring Boot。负责配置管理、发版排错。核心任务是串联“智能体请求 -> 安全拦截 -> 双跑 SQL -> 比对结果 -> LLM 异常诊断”。
3. **Execution Engine (执行任务引擎)**: 必须具备**限流与退避重试**能力，保护待测智能体；沙箱查询请求必须带有**严格的超时中断机制（如设定5秒强制Kill）**。
4. **Sandbox DB (专有沙箱数据库)**: 针对被测业务的“影子库”。后台数据库连接账户**必须只赋予 SELECT 权限**，物理层面杜绝任何修改/截断风险。

## 二、 数据库表结构设计 (ER 草案)

基于 PRD 第四部分的指引，梳理五大核心主表：

### 1. 资产环境表 (`schema_env`)
管理 DDL 及连接配置。
- `id`: 主键
- `env_name`: 环境名称（如 "电商核心业务库"）
- `ddl_content`: 建表语句集合
- `sandbox_db_url`: 沙箱库只读连接串
- `created_at` / `updated_at`

### 2. 基准测试集表 (`test_case`)
存储跑成功、清洗过的高质量用例。
- `id`: 主键
- `env_id`: 关联 `schema_env`
- `question`: 业务自然语言问题
- `golden_sql`: 标准答案 SQL (已经在沙箱试跑通过的)
- `tags`: JSON，业务标签（如 `["多表关联", "日期过滤"]`）
- `created_at` / `updated_at`

### 3. 智能体配置表 (`agent_config`)
存储待测目标及限流防护配置。
- `id`: 主键
- `agent_name`: 智能体名称
- `api_endpoint`: 请求地址
- `auth_token`: 鉴权 Token
- `rate_limit_qps`: 并发数上限
- `timeout_ms`: 请求大模型的超时阈值

### 4. 批量评测任务表 (`evaluation_task`)
宏观任务跟踪。
- `id`: 主键
- `task_name`: 任务名称
- `agent_id`: 关联 `agent_config`
- `env_id`: 关联测试环境
- `judge_llm_model`: 高阶诊断模型（如 GPT-4 / null 表示不启用）
- `status`: 状态 (Pending, Running, Completed, Failed)
- `stats_json`: 统计快照（成功率、超时率、错误分类计数等）
- `created_at` / `completed_at`

### 5. 核心评测结果明细表 (`evaluation_result`)
原子级别的逐条对比跟踪与高阶诊断结果。
- `id`: 主键
- `task_id`: 关联任务
- `case_id`: 关联用例 `test_case`
- `agent_sql`: 智能体返回的测试 SQL
- `execution_status`: 执行状态枚举 (Success, Syntax_Error, Timeout, Security_Blocked)
- `golden_data_hash`: 标准 SQL 结果集的 Hash（或直接存 JSON，若数据不大）
- `agent_data_hash`: 测试 SQL 结果集的 Hash
- `data_diff_passed`: 结果集是否 100% 匹配 (Boolean)
- `ai_diagnosis`: 大模型作为裁判给出的长文本错因分析（如 “遗漏了 WHERE 软删除条件”）
- `execution_time_ms`: 请求及执行总耗时

## 三、 Backend 执行引擎：基于“盲测与沙箱双跑”的核心伪代码

```python
import asyncio
import hashlib

async def execute_evaluation_case(task_config, test_case):
    # 1. 盲测获取 (Blind Testing)
    # 仅发送问题和DDL，获取智能体生成的 SQL (带有退避重试保护)
    test_sql, agent_err = await fetch_sql_from_agent_with_retry(
        task_config.agent, 
        test_case.question, 
        task_config.env.ddl_content
    )
    
    if agent_err:
        await save_result(execution_status="Agent_API_Error")
        return

    # 2. 安全拦截 (Security Filter)
    if is_unsafe_sql(test_sql):
        await save_result(test_sql, execution_status="Security_Blocked", data_diff_passed=False)
        return

    # 3. 强制包装 LIMIT
    safe_test_sql = enforce_limit(test_sql, limit=100)
    safe_golden_sql = enforce_limit(test_case.golden_sql, limit=100)

    # 4. 沙箱双跑 (Execution in Sandbox with Timeout)
    try:
        # 并发执行两条 SQL，限制执行超时如 5 秒
        golden_data, test_data = await asyncio.gather(
            execute_sql_in_sandbox(task_config.env.sandbox_db_url, safe_golden_sql),
            execute_sql_in_sandbox(task_config.env.sandbox_db_url, safe_test_sql),
        )
    except TimeoutError:
        await save_result(safe_test_sql, execution_status="Timeout", data_diff_passed=False)
        return
    except SyntaxError as e:
        # 记录报错原因用于传给 LLM 诊断
        await save_result(safe_test_sql, execution_status="Syntax_Error", data_diff_passed=False, error_msg=str(e))
        return

    # 5. Data Diff 结果集比对 (比对核心要素而不是完全比对JSON字符串)
    is_passed = compare_result_sets(golden_data, test_data)

    # 6. 高阶兜底诊断 (LLM Judge) -- 仅在比对失败时触发
    ai_diagnosis = ""
    if not is_passed and task_config.judge_llm_model:
        ai_diagnosis = await call_llm_for_diagnosis(
            model=task_config.judge_llm_model,
            question=test_case.question,
            golden_sql=test_case.golden_sql,
            test_sql=safe_test_sql,
            golden_data_sample=golden_data[:2],  # 提供少量数据切片辅助判断
            test_data_sample=test_data[:2]
        )

    # 7. 结果落库
    await save_result(
        task_id=task_config.id,
        case_id=test_case.id,
        agent_sql=safe_test_sql,
        execution_status="Success",
        data_diff_passed=is_passed,
        ai_diagnosis=ai_diagnosis
    )
```

## 四、 后续行动
这个基于“真实执行与数据比对”的版本更贴近实际生产场景。
我们可以直接基于这一版架构进行：
1. **Python 后端核心流程编码** 或 
2. **建表脚本 (MySQL 等) 生成**。

您目前更希望我先推进哪一步？
