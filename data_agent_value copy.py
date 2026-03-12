import asyncio
import pandas as pd
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from deepeval.metrics import BaseMetric, GEval
from deepeval.models.llms import GPTModel
import requests
import json
import random
import time


def get_sso_token():
    """通过SSO登录获取token"""
    # 第一步：获取ticket
    url = "https://user.binarysee.com.cn/api/iam/sso/login-with-password"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    data = {
        "account": "13439427048",
        "password": "Zsh@417418",
    }
    
    response = requests.post(url=url, headers=headers, json=data)
    ticket = response.json()["data"]["ticket"]
    print(f"获取ticket成功: {ticket}")
    
    # 第二步：使用ticket获取token
    url = "http://113.44.121.105:8910/sso/login"
    data = {"ticket": ticket}
    response = requests.post(url=url, headers=headers, json=data).json()
    token = response["data"]["token"]
    print(f"获取token成功: {token}")
    
    return token


# 获取SSO token
token = get_sso_token()

class BrainFAQConfig:
    """Brain FAQ 接口配置"""

    BASE_URL = "http://1.92.195.88/brain/faq/session/ask"
    TENANT_ID = "1916705084137349121"

    def __init__(self, robot_id=None, robot_biz_id=None, chat_id=None):
        """初始化配置，支持自定义参数"""
        self.ROBOT_ID = robot_id 
        self.ROBOT_BIZ_ID = robot_biz_id
        self.CHAT_ID = chat_id 
        self.AUTHORIZATION = token
        
        self.HEADERS = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "Authorization": self.AUTHORIZATION,
            "tenant-id": self.TENANT_ID,
            "User-Agent": "Mozilla/5.0",
        }


class BrainFAQClient:
    def __init__(self, config=None):
        """初始化客户端"""
        self.config = config or BrainFAQConfig()
        self.url = self.config.BASE_URL
        self.robot_id = self.config.ROBOT_ID
        self.robotBizId = self.config.ROBOT_BIZ_ID
        self.chatId = self.config.CHAT_ID
        self.headers = self.config.HEADERS

    def _generate_id(self):
        return int(str(int(time.time() * 1000)) + str(random.randint(100, 999)))

    def ask_for_sql(self, user_input: str) -> str:
        payload = {
            "robot_id": self.robot_id,
            "robotBizId": self.robotBizId,
            "incremental": False,
            "status": "1",
            "chatId": self.chatId,
            "user_input": user_input,
            "newChatId": None,
            "answerId": self._generate_id(),
            "askId": self._generate_id(),
            "pageNum": 1,
            "pageSize": 10,
            "appId": "0",
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "Authorization": token,
            "tenant-id": "1916705084137349121",
            "User-Agent": "Mozilla/5.0",
        }

        with requests.post(
            self.url, json=payload, headers=headers, stream=True, timeout=60
        ) as response:
            response.raise_for_status()

            found_start = False

            for raw_line in response.iter_lines():
                if not raw_line:
                    continue
                raw_line = raw_line.decode("utf-8")
                if raw_line.startswith("data:"):
                    line = raw_line.replace("data:", "").strip()

                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    # 找到 START
                    if data.get("type") == "ANSWER" and data.get("status") == "START":
                        found_start = True
                        continue

                    # START 后第一条
                    if found_start:
                        # SQL执行失败
                        if data.get("status") == -1:
                            return "SQL_EXECUTION_FAILED"

                        try:
                            content = data.get("content", {})
                            if isinstance(content, str):
                                content = json.loads(content)

                            visual = content.get("visual", {})
                            sql = visual.get("sql")

                            if sql:
                                return sql

                        except Exception:
                            return "SQL_PARSE_FAILED"

        return "SQL_GENERATE_FAILED"


# ===========================
# 1. 裁判模型配置 (优化点：统一配置接口)
# ===========================
# 裁判模型配置 - 设为 None 时不进行语义评估
ENABLE_JUDGE_MODEL = False  # 是否启用裁判模型

if ENABLE_JUDGE_MODEL:
    qwen_judge = GPTModel(
        model="qwen-max",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key="23232eeweew3333"
        # api_key="sk-0b4c79748dc04bd8bebbadde4a566fba",  # 请替换为真实 Key
    )
else:
    qwen_judge = None
    print("裁判模型已禁用，将使用简化评估逻辑")


# ===========================
# 2. 自定义 SQL 语义等价指标 (优化点：鲁棒的 JSON 解析与思维链)
# ===========================
class SQLSemanticCorrectnessMetric(BaseMetric):
    def __init__(self, model, threshold=80):
        self.model = model
        self.threshold = threshold
        self.score = 0
        self.reason = ""

    def measure(self, test_case: LLMTestCase):
        # 同步方法内部调用异步逻辑
        return asyncio.run(self.a_measure(test_case))

    async def a_measure(self, test_case: LLMTestCase, **kwargs):
        prompt = f"""
                    你是一位资深的数据库专家。请对比【模型生成 SQL】与【基准 SQL】的逻辑等价性。
                    
                    [上下文信息]
                    原始问题: {test_case.input}
                    
                    [SQL 对比]
                    基准 SQL:{test_case.expected_output}
                    模型生成 SQL: {test_case.actual_output}
                    
                    [判定标准]
                    1. 逻辑等价：即使语法不同（如 JOIN vs IN），只要在上述表结构下结果集一致，即为满分。
                    2. 字段准确性：SELECT 的字段是否符合问题要求。
                    3. 过滤条件：WHERE 字句逻辑是否严格匹配。
                    
                    请严格按以下 JSON 格式返回，不要包含其他文字：
                    {{"score": 评分0到1, "reason": "具体失败原因或通过理由"}}
                    """
        raw_res = self.model.generate(prompt)

        if isinstance(raw_res, tuple):
            raw_res = raw_res[0]
        try:
            # 清理可能存在的 Markdown 格式
            clean_res = raw_res.strip().replace("```json", "").replace("```", "")
            data = json.loads(clean_res)
            self.score = float(data.get("score", 0))
            self.reason = data.get("reason", "No reason provided")
        except Exception as e:
            self.score = 0
            self.reason = f"解析裁判输出失败: {str(e)}"

        self.success = self.score >= self.threshold
        return self.score

    def is_successful(self):
        return self.success

    @property
    def __name__(self):
        return "SQL 语义等价性"


# ===========================
# 3. 增加维度：SQL 性能与风格指标 (优化点：利用原生 GEval)
# ===========================
if ENABLE_JUDGE_MODEL:
    sql_efficiency_metric = GEval(
        name="SQL 性能与规范",
        model=qwen_judge,
        criteria="评估 SQL 是否包含不必要的 SELECT *，是否正确使用了 GROUP BY，以及是否存在潜在的性能问题。",
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        threshold=0.7,
    )
else:
    sql_efficiency_metric = None


# ===========================
# 4. 数据智能体 (保持原样，仅做示例)
# ===========================
class DataAgent:
    def __init__(self):
        self.client = BrainFAQClient()

    def generate_sql(self, question: str) -> str:
        try:
            sql = self.client.ask_for_sql(question)
            return sql if sql else ""
        except Exception as e:
            print(f"接口调用失败: {e}")
            return ""


def excel_to_dataset(
    excel_path: str, question_col: str = None, sql_col: str = None
) -> list:
    """
    将 Excel 转换为 dataset 列表，每条数据格式如下：
    {
        "question": "问题内容",
        "golden_sql": "对应 SQL"
    }

    参数:
    - excel_path: Excel 文件路径
    - question_col: 问题列名（有表头时填，如 '问题'，无表头则 None）
    - sql_col: SQL 列名（有表头时填，如 'SQL'，无表头则 None）

    返回:
    - list[dict]，每条 dict 包含 question 和 golden_sql
    """
    df = pd.read_excel(excel_path, header=0 if question_col else None)

    dataset = []
    for idx, row in df.iterrows():
        # 有表头则用列名，否则用索引 0/1
        question = row[question_col] if question_col else row[0]
        golden_sql = row[sql_col] if sql_col else row[1]
        dataset.append({"question": question, "golden_sql": golden_sql})

    return dataset


# ===========================
# 5. 测试执行引擎 (优化点：使用 pytest 风格的组织方式)
# ===========================
def test_single_agent(robot_id, robot_biz_id, chat_id, excel_path, agent_name=""):
    """
    测试单个智能体的 SQL 生成能力
    
    Args:
        robot_id: 机器人ID
        robot_biz_id: 机器人业务ID
        chat_id: 聊天ID
        excel_path: 测试数据集路径
        agent_name: 智能体名称（用于报告）
    
    Returns:
        list: 测试结果列表
    """
    print(f"\n{'='*60}")
    print(f"开始测试智能体: {agent_name}")
    print(f"ROBOT_ID: {robot_id}")
    print(f"Excel路径: {excel_path}")
    print(f"{'='*60}")
    
    # 使用参数化配置初始化智能体
    config = BrainFAQConfig()
    config.ROBOT_ID = str(robot_id)
    config.ROBOT_BIZ_ID = int(robot_biz_id)
    config.CHAT_ID = int(chat_id)
    
    agent = DataAgent()
    agent.client = BrainFAQClient(config)
    
    # 加载数据集
    try:
        dataset = excel_to_dataset(excel_path, question_col="问题", sql_col="结果")
    except Exception as e:
        print(f"加载数据集失败: {e}")
        return []
    
    results = []
    
    for idx, case in enumerate(dataset, 1):
        print(f"\n[{agent_name}] 处理第 {idx}/{len(dataset)} 个问题...")
        
        actual_sql = agent.generate_sql(case["question"])
        
        # 简化的评估逻辑（当裁判模型禁用时使用）
        semantic_score = 0.0
        semantic_reason = ""
        efficiency_score = 0.0
        
        # 相似度检测结果（基于SQL生成是否成功）
        is_similar = False
        if actual_sql and "SQL_EXECUTION_FAILED" not in actual_sql and "SQL_PARSE_FAILED" not in actual_sql and "SQL_GENERATE_FAILED" not in actual_sql:
            is_similar = True
        
        if ENABLE_JUDGE_MODEL and qwen_judge:
            # 使用裁判模型进行评估
            semantic_metric = SQLSemanticCorrectnessMetric(model=qwen_judge)
            test_case = LLMTestCase(
                input=case["question"],
                actual_output=actual_sql,
                expected_output=case["golden_sql"],
            )
            # 手动执行评测（不会抛异常）
            semantic_metric.measure(test_case)
            if sql_efficiency_metric:
                sql_efficiency_metric.measure(test_case)
                efficiency_score = sql_efficiency_metric.score
            semantic_score = semantic_metric.score
            semantic_reason = semantic_metric.reason
        else:
            # 使用简化评估逻辑
            if is_similar:
                semantic_score = 0.8  # SQL生成成功，假设基本正确
                semantic_reason = "SQL生成成功（简化评估）"
            else:
                semantic_score = 0.0
                semantic_reason = "SQL生成失败（简化评估）"
            
            # 简单的SQL规范评估
            if actual_sql and "SELECT *" not in actual_sql:
                efficiency_score = 0.9
            else:
                efficiency_score = 0.5
        
        total_score = 0.6 * semantic_score + efficiency_score * 0.4
        
        result = {
            "agent_name": agent_name,
            "robot_id": robot_id,
            "question": case["question"],
            "golden_sql": case["golden_sql"],
            "actual_sql": actual_sql,
            "semantic_score": semantic_score,
            "semantic_reason": semantic_reason,
            "efficiency_score": efficiency_score,
            "total_score": total_score,
            "is_similar": is_similar,  # 相似度检测结果
        }
        
        results.append(result)
        
        print("问题:", case["question"])
        print("生成SQL:", actual_sql)
        print("语义得分:", semantic_score)
        print("SQL规范得分:", efficiency_score)
        print("相似度检测:", "通过" if is_similar else "不通过")
    
    print(f"\n智能体 {agent_name} 测试完成，共 {len(results)} 个case")
    return results


def test_data_agent_sql():
    """
    从配置Excel读取多个智能体配置，循环执行测试
    配置Excel格式：
    | ROBOT_ID | ROBOT_BIZ_ID | CHAT_ID | excel_path | agent_name |
    """
    # 配置Excel路径 - 包含所有智能体配置信息
    config_excel_path = r"D:\智能体配置.xlsx"
    
    try:
        # 读取配置
        config_df = pd.read_excel(config_excel_path)
        print(f"成功读取配置，共 {len(config_df)} 个智能体")
    except Exception as e:
        print(f"读取配置Excel失败: {e}")
        print("请确保配置文件存在且格式正确")
        return
    
    all_results = []
    
    # 循环遍历每个智能体配置
    for idx, row in config_df.iterrows():
        robot_id = str(row.get("ROBOT_ID", ""))
        robot_biz_id = row.get("ROBOT_BIZ_ID", 0)
        chat_id = row.get("CHAT_ID", 0)
        excel_path = row.get("excel_path", "")
        agent_name = row.get("agent_name", f"智能体_{idx+1}")
        
        # 验证必要参数
        if not robot_id or not excel_path:
            print(f"跳过第 {idx+1} 行：缺少必要参数")
            continue
        
        # 执行单个智能体测试
        try:
            results = test_single_agent(
                robot_id=robot_id,
                robot_biz_id=int(robot_biz_id),
                chat_id=int(chat_id),
                excel_path=excel_path,
                agent_name=agent_name
            )
            all_results.extend(results)
        except Exception as e:
            print(f"测试智能体 {agent_name} 时出错: {e}")
            continue
    
    # 生成汇总报告
    if all_results:
        df = pd.DataFrame(all_results)
        output_file = "nl2sql_multi_agent_test_report.xlsx"
        df.to_excel(output_file, index=False)
        print(f"\n{'='*60}")
        print(f"所有测试完成！")
        print(f"总测试case数: {len(all_results)}")
        print(f"报告已生成: {output_file}")
        print(f"{'='*60}")
    else:
        print("没有生成任何测试结果")


if __name__ == "__main__":
    # 使用 deepeval 的执行器运行，这会自动生成漂亮的终端报告
    # 在命令行运行: deepeval test run deepeval_sql_eval.py
    
    # 方式1: 从配置Excel读取多个智能体配置并循环执行
    test_data_agent_sql()
    
    # 方式2: 单独测试单个智能体（如需快速测试）
    # results = test_single_agent(
    #     robot_id="8974853165260833",
    #     robot_biz_id=8974853165260923,
    #     chat_id=7708044628595567,
    #     excel_path=r"D:\汽车智能体问题.xlsx",
    #     agent_name="汽车智能体"
    # )
