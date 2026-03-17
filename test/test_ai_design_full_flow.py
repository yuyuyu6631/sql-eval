import sys
from pathlib import Path

import httpx
import pytest
from sqlalchemy import delete


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import AsyncSessionLocal, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.ai_test_design import AITestCase, AITestPoint, DesignResult, KnowledgeSource  # noqa: E402
from app.models.model_provider_config import ModelProviderConfig  # noqa: E402


async def _cleanup_test_data():
    async with AsyncSessionLocal() as db:
        await db.execute(delete(AITestCase))
        await db.execute(delete(AITestPoint))
        await db.execute(delete(DesignResult))
        await db.execute(delete(KnowledgeSource))
        await db.execute(delete(ModelProviderConfig).where(ModelProviderConfig.name.like("test-ai-design-%")))
        await db.commit()


@pytest.mark.asyncio
async def test_ai_design_forward_full_flow():
    await init_db()
    await _cleanup_test_data()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        knowledge_resp = await client.post(
            "/api/ai-test-design/knowledge",
            json={
                "title": "test-ai-design-login",
                "module_name": "登录中心",
                "content": "用户通过手机号和验证码登录，验证码5分钟有效，连续失败5次后限制重试。",
                "extra_instruction": "优先覆盖异常流程、边界值和限制重试逻辑。",
                "source_type": "manual",
            },
        )
        assert knowledge_resp.status_code == 200
        knowledge_id = knowledge_resp.json()["id"]

        design_resp = await client.post(
            "/api/ai-test-design/design/generate",
            json={"knowledge_id": knowledge_id, "design_mode": "standard"},
        )
        assert design_resp.status_code == 200
        design_id = design_resp.json()["design_id"]
        assert design_resp.json()["source"] in {"ai", "fallback"}
        assert isinstance(design_resp.json()["summary"]["function_scope"], list)

        points_resp = await client.post(
            "/api/ai-test-design/points/generate",
            json={"design_id": design_id},
        )
        assert points_resp.status_code == 200
        points = points_resp.json()["points"]
        assert len(points) >= 1
        point_ids = [point["id"] for point in points[:2]]

        cases_resp = await client.post(
            "/api/ai-test-design/cases/generate",
            json={
                "design_id": design_id,
                "point_ids": point_ids,
                "case_type": "functional",
                "generate_mode": "standard",
                "output_count": 4,
            },
        )
        assert cases_resp.status_code == 200
        assert len(cases_resp.json()["cases"]) >= 1

        list_resp = await client.get("/api/ai-test-design/test-cases/list", params={"design_id": design_id})
        assert list_resp.status_code == 200
        listed_cases = list_resp.json()
        assert len(listed_cases) >= 1
        case_id = listed_cases[0]["id"]

        edit_resp = await client.put(
            f"/api/ai-test-design/test-cases/{case_id}",
            json={
                "title": "登录异常流程-编辑后",
                "status": "confirmed",
                "steps": ["输入手机号", "输入错误验证码", "点击登录"],
                "expected_result": "系统提示验证码错误且记录失败次数",
            },
        )
        assert edit_resp.status_code == 200

        detail_resp = await client.get(f"/api/ai-test-design/test-cases/{case_id}")
        assert detail_resp.status_code == 200
        assert detail_resp.json()["title"] == "登录异常流程-编辑后"
        assert detail_resp.json()["status"] == "confirmed"

        export_md_resp = await client.post(
            "/api/ai-test-design/test-cases/export",
            json={"design_id": design_id, "format": "markdown"},
        )
        assert export_md_resp.status_code == 200
        assert export_md_resp.text.strip().startswith("# ")

        export_json_resp = await client.post(
            "/api/ai-test-design/test-cases/export",
            json={"design_id": design_id, "format": "json"},
        )
        assert export_json_resp.status_code == 200
        assert export_json_resp.text.strip().startswith("[")

        delete_resp = await client.delete(f"/api/ai-test-design/test-cases/{case_id}")
        assert delete_resp.status_code == 200

        final_list_resp = await client.get("/api/ai-test-design/test-cases/list", params={"design_id": design_id})
        assert final_list_resp.status_code == 200
        remaining_ids = [item["id"] for item in final_list_resp.json()]
        assert case_id not in remaining_ids


@pytest.mark.asyncio
async def test_ai_design_reverse_regenerate_flow():
    await init_db()
    await _cleanup_test_data()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        knowledge_resp = await client.post(
            "/api/ai-test-design/knowledge",
            json={
                "title": "test-ai-design-order-refund",
                "module_name": "退款中心",
                "content": "订单支持全额退款和部分退款，已发货订单需校验退款资格，同一订单不能重复发起相同退款单。",
                "extra_instruction": "重点覆盖重复提交、资格校验和状态回退。",
                "source_type": "manual",
            },
        )
        assert knowledge_resp.status_code == 200
        knowledge_id = knowledge_resp.json()["id"]

        design_resp = await client.post(
            "/api/ai-test-design/design/generate",
            json={"knowledge_id": knowledge_id, "design_mode": "deep"},
        )
        assert design_resp.status_code == 200
        design_id = design_resp.json()["design_id"]

        points_resp = await client.post(
            "/api/ai-test-design/points/generate",
            json={"design_id": design_id},
        )
        assert points_resp.status_code == 200
        points = points_resp.json()["points"]
        assert len(points) >= 2

        selected_point_ids = [point["id"] for point in points[:2]]
        first_generate_resp = await client.post(
            "/api/ai-test-design/cases/generate",
            json={
                "design_id": design_id,
                "point_ids": selected_point_ids,
                "case_type": "functional",
                "generate_mode": "standard",
                "output_count": 3,
            },
        )
        assert first_generate_resp.status_code == 200
        assert len(first_generate_resp.json()["cases"]) >= 1

        unselect_resp = await client.put(
            f"/api/ai-test-design/test-points/{selected_point_ids[1]}",
            json={"selected": False},
        )
        assert unselect_resp.status_code == 200

        points_list_resp = await client.get("/api/ai-test-design/test-points/list", params={"design_id": design_id})
        assert points_list_resp.status_code == 200
        refreshed_points = points_list_resp.json()
        selected_after_reverse = [point["id"] for point in refreshed_points if point["selected"]]
        assert selected_point_ids[1] not in selected_after_reverse
        assert selected_point_ids[0] in selected_after_reverse

        second_generate_resp = await client.post(
            "/api/ai-test-design/cases/generate",
            json={
                "design_id": design_id,
                "point_ids": [selected_point_ids[0]],
                "case_type": "functional",
                "generate_mode": "simple",
                "output_count": 2,
            },
        )
        assert second_generate_resp.status_code == 200
        assert len(second_generate_resp.json()["cases"]) >= 1

        case_list_resp = await client.get("/api/ai-test-design/test-cases/list", params={"design_id": design_id})
        assert case_list_resp.status_code == 200
        assert len(case_list_resp.json()) >= 1

        case_id = case_list_resp.json()[0]["id"]
        confirm_resp = await client.put(
            f"/api/ai-test-design/test-cases/{case_id}",
            json={"status": "confirmed"},
        )
        assert confirm_resp.status_code == 200

        detail_resp = await client.get(f"/api/ai-test-design/test-cases/{case_id}")
        assert detail_resp.status_code == 200
        assert detail_resp.json()["status"] == "confirmed"
