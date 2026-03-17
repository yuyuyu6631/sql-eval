import csv
import io
import json
from pathlib import Path
from typing import Optional, Literal, Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from openpyxl import Workbook

from app.database import get_db
from app.models.ai_test_design import KnowledgeSource, DesignResult, AITestPoint, AITestCase
from app.services.ai_provider import get_enabled_provider_by_usage, call_openai_compatible_json, log_ai_fallback

router = APIRouter(prefix="/ai-test-design")

CATEGORIES = ["正常流程", "异常流程", "边界值", "权限控制", "状态流转", "其他"]


class KnowledgeCreate(BaseModel):
    title: str
    module_name: Optional[str] = None
    content: str
    extra_instruction: Optional[str] = None
    source_type: str = "manual"


class KnowledgeResponse(KnowledgeCreate):
    id: int

    model_config = ConfigDict(from_attributes=True)


class DesignGenerateRequest(BaseModel):
    knowledge_id: int
    model_name: Optional[str] = None
    design_mode: Literal["simple", "standard", "deep"] = "standard"


class TestPointGenerateRequest(BaseModel):
    design_id: int
    model_name: Optional[str] = None


class TestPointUpdateRequest(BaseModel):
    category: Optional[str] = None
    content: Optional[str] = None
    priority: Optional[Literal["P0", "P1", "P2", "P3"]] = None
    selected: Optional[bool] = None


class TestPointBatchSelectRequest(BaseModel):
    ids: list[int]
    selected: bool


class CaseGenerateRequest(BaseModel):
    design_id: int
    point_ids: list[int]
    model_name: Optional[str] = None
    case_type: Literal["functional", "api", "ui", "generic"] = "functional"
    generate_mode: Literal["simple", "standard", "deep"] = "standard"
    output_count: int = 20


class CaseUpdateRequest(BaseModel):
    title: Optional[str] = None
    precondition: Optional[str] = None
    steps: Optional[list[str]] = None
    expected_result: Optional[str] = None
    priority: Optional[Literal["P0", "P1", "P2", "P3"]] = None
    case_type: Optional[Literal["functional", "api", "ui", "generic"]] = None
    status: Optional[Literal["new", "confirmed", "optimize_needed"]] = None


class ExportRequest(BaseModel):
    design_id: int
    format: Literal["markdown", "json", "csv", "xlsx"] = "markdown"


@router.post("/knowledge")
async def create_knowledge(payload: KnowledgeCreate, db: AsyncSession = Depends(get_db)):
    row = KnowledgeSource(**payload.model_dump())
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {"id": row.id, "message": "知识输入保存成功"}


@router.get("/knowledge/list", response_model=list[KnowledgeResponse])
async def list_knowledge(
    keyword: Optional[str] = None,
    module_name: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(KnowledgeSource).order_by(KnowledgeSource.id.desc())
    if module_name:
        query = query.where(KnowledgeSource.module_name == module_name)
    if keyword:
        like = f"%{keyword}%"
        query = query.where(KnowledgeSource.title.ilike(like) | KnowledgeSource.content.ilike(like))
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/knowledge/import")
async def import_knowledge_file(
    file: UploadFile = File(...),
    title: Optional[str] = None,
    module_name: Optional[str] = None,
    extra_instruction: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    filename = file.filename or "knowledge.txt"
    ext = Path(filename).suffix.lower()
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="上传文件为空")

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("gbk", errors="ignore")

    if ext == ".json":
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                text = json.dumps(parsed, ensure_ascii=False, indent=2)
        except Exception:
            pass

    row = KnowledgeSource(
        title=(title or Path(filename).stem or "导入知识").strip(),
        module_name=(module_name or "").strip() or None,
        content=text.strip(),
        extra_instruction=(extra_instruction or "").strip() or None,
        source_type="file_import",
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {"id": row.id, "message": "文件导入成功", "filename": filename, "size": len(raw)}


@router.get("/knowledge/{knowledge_id}", response_model=KnowledgeResponse)
async def get_knowledge(knowledge_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeSource).where(KnowledgeSource.id == knowledge_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Knowledge not found")
    return row


@router.delete("/knowledge/{knowledge_id}")
async def delete_knowledge(knowledge_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeSource).where(KnowledgeSource.id == knowledge_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Knowledge not found")
    await db.delete(row)
    await db.commit()
    return {"ok": True}


@router.post("/design/generate")
async def generate_design(payload: DesignGenerateRequest, db: AsyncSession = Depends(get_db)):
    knowledge = await _get_or_404(db, KnowledgeSource, payload.knowledge_id, "Knowledge not found")
    summary = await _generate_design_summary(db, knowledge, payload)

    row = DesignResult(
        knowledge_id=knowledge.id,
        model_name=payload.model_name or summary.get("model_name"),
        design_mode=payload.design_mode,
        function_scope=summary.get("function_scope", []),
        coverage_dimensions=summary.get("coverage_dimensions", []),
        risks=summary.get("risks", []),
        missing_info=summary.get("missing_info", []),
        raw_output=summary.get("raw_output"),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {
        "design_id": row.id,
        "summary": {
            "function_scope": row.function_scope,
            "coverage_dimensions": row.coverage_dimensions,
            "risks": row.risks,
            "missing_info": row.missing_info,
        },
        "source": summary.get("source", "fallback"),
        "fallback_reason": summary.get("fallback_reason"),
        "model_name": summary.get("model_name"),
        "model_raw_output": (summary.get("raw_output") or "")[:1000],
    }


@router.get("/design/{design_id}")
async def get_design(design_id: int, db: AsyncSession = Depends(get_db)):
    row = await _get_or_404(db, DesignResult, design_id, "Design not found")
    return {
        "id": row.id,
        "knowledge_id": row.knowledge_id,
        "model_name": row.model_name,
        "design_mode": row.design_mode,
        "summary": {
            "function_scope": row.function_scope,
            "coverage_dimensions": row.coverage_dimensions,
            "risks": row.risks,
            "missing_info": row.missing_info,
        },
        "raw_output": row.raw_output,
    }


@router.post("/points/generate")
async def generate_test_points(payload: TestPointGenerateRequest, db: AsyncSession = Depends(get_db)):
    design = await _get_or_404(db, DesignResult, payload.design_id, "Design not found")
    point_result = await _generate_points_from_design(db, design, payload.model_name)
    points = point_result["points"]

    for idx, point in enumerate(points):
        db.add(
            AITestPoint(
                design_id=design.id,
                category=point["category"],
                content=point["content"],
                priority=point["priority"],
                selected=point.get("selected", True),
                sort_order=idx,
            )
        )
    await db.commit()

    result = await db.execute(select(AITestPoint).where(AITestPoint.design_id == design.id).order_by(AITestPoint.sort_order.asc(), AITestPoint.id.asc()))
    rows = result.scalars().all()
    return {
        "design_id": design.id,
        "points": [
            {
                "id": r.id,
                "category": r.category,
                "content": r.content,
                "priority": r.priority,
                "selected": r.selected,
            }
            for r in rows
        ],
        "source": point_result.get("source", "fallback"),
        "fallback_reason": point_result.get("fallback_reason"),
        "model_name": point_result.get("model_name"),
        "model_raw_output": (point_result.get("raw_output") or "")[:1000],
    }


@router.get("/test-points/list")
async def list_test_points(design_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AITestPoint).where(AITestPoint.design_id == design_id).order_by(AITestPoint.sort_order.asc(), AITestPoint.id.asc()))
    rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "design_id": r.design_id,
            "category": r.category,
            "content": r.content,
            "priority": r.priority,
            "selected": r.selected,
        }
        for r in rows
    ]


@router.put("/test-points/{point_id}")
async def update_test_point(point_id: int, payload: TestPointUpdateRequest, db: AsyncSession = Depends(get_db)):
    row = await _get_or_404(db, AITestPoint, point_id, "Test point not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    await db.commit()
    await db.refresh(row)
    return {"id": row.id, "message": "updated"}


@router.put("/test-points/batch-select")
async def batch_select_test_points(payload: TestPointBatchSelectRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AITestPoint).where(AITestPoint.id.in_(payload.ids)))
    rows = result.scalars().all()
    for row in rows:
        row.selected = payload.selected
    await db.commit()
    return {"updated_count": len(rows)}


@router.delete("/test-points/{point_id}")
async def delete_test_point(point_id: int, db: AsyncSession = Depends(get_db)):
    row = await _get_or_404(db, AITestPoint, point_id, "Test point not found")
    await db.delete(row)
    await db.commit()
    return {"ok": True}


@router.post("/cases/generate")
async def generate_test_cases(payload: CaseGenerateRequest, db: AsyncSession = Depends(get_db)):
    design = await _get_or_404(db, DesignResult, payload.design_id, "Design not found")
    result = await db.execute(select(AITestPoint).where(AITestPoint.id.in_(payload.point_ids)))
    points = result.scalars().all()
    if not points:
        raise HTTPException(status_code=400, detail="No test points selected")

    case_result = await _generate_cases_from_points(db, design, points, payload)
    generated = case_result["cases"]
    for item in generated:
        db.add(
            AITestCase(
                design_id=design.id,
                point_id=item.get("point_id"),
                title=item["title"],
                precondition=item.get("precondition"),
                steps=item.get("steps", []),
                expected_result=item["expected_result"],
                case_type=item.get("case_type", payload.case_type),
                priority=item.get("priority", "P1"),
                coverage_dimension=item.get("coverage_dimension"),
                status="new",
                model_name=item.get("model_name"),
                raw_output=item.get("raw_output"),
            )
        )
    await db.commit()
    return {
        "cases": generated,
        "source": case_result.get("source", "fallback"),
        "fallback_reason": case_result.get("fallback_reason"),
        "model_name": case_result.get("model_name"),
        "model_raw_output": (case_result.get("raw_output") or "")[:1000],
    }


@router.get("/test-cases/list")
async def list_generated_cases(
    design_id: int,
    keyword: Optional[str] = None,
    case_type: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(AITestCase).where(AITestCase.design_id == design_id).order_by(AITestCase.id.desc())
    if keyword:
        like = f"%{keyword}%"
        query = query.where(AITestCase.title.ilike(like) | AITestCase.expected_result.ilike(like))
    if case_type:
        query = query.where(AITestCase.case_type == case_type)
    if status:
        query = query.where(AITestCase.status == status)
    if priority:
        query = query.where(AITestCase.priority == priority)
    result = await db.execute(query)
    rows = result.scalars().all()
    return [_case_to_dict(r) for r in rows]


@router.get("/test-cases/{case_id}")
async def get_generated_case(case_id: int, db: AsyncSession = Depends(get_db)):
    row = await _get_or_404(db, AITestCase, case_id, "Test case not found")
    return _case_to_dict(row)


@router.put("/test-cases/{case_id}")
async def update_generated_case(case_id: int, payload: CaseUpdateRequest, db: AsyncSession = Depends(get_db)):
    row = await _get_or_404(db, AITestCase, case_id, "Test case not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    await db.commit()
    await db.refresh(row)
    return {"id": row.id, "message": "updated"}


@router.delete("/test-cases/{case_id}")
async def delete_generated_case(case_id: int, db: AsyncSession = Depends(get_db)):
    row = await _get_or_404(db, AITestCase, case_id, "Test case not found")
    await db.delete(row)
    await db.commit()
    return {"ok": True}


@router.post("/test-cases/{case_id}/copy")
async def copy_generated_case(case_id: int, db: AsyncSession = Depends(get_db)):
    row = await _get_or_404(db, AITestCase, case_id, "Test case not found")
    copied = AITestCase(
        design_id=row.design_id,
        point_id=row.point_id,
        title=f"{row.title} - Copy",
        precondition=row.precondition,
        steps=row.steps,
        expected_result=row.expected_result,
        case_type=row.case_type,
        priority=row.priority,
        coverage_dimension=row.coverage_dimension,
        status="new",
        model_name=row.model_name,
        raw_output=row.raw_output,
    )
    db.add(copied)
    await db.commit()
    await db.refresh(copied)
    return _case_to_dict(copied)


@router.post("/test-cases/export")
async def export_cases(payload: ExportRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AITestCase).where(AITestCase.design_id == payload.design_id).order_by(AITestCase.id.asc()))
    rows = result.scalars().all()
    cases = [_case_to_dict(r) for r in rows]

    if payload.format == "json":
        content = json.dumps(cases, ensure_ascii=False, indent=2, default=str)
        return StreamingResponse(io.StringIO(content), media_type="application/json")

    if payload.format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "title", "case_type", "priority", "status", "precondition", "steps", "expected_result"])
        for item in cases:
            writer.writerow([
                item["id"],
                item["title"],
                item["case_type"],
                item["priority"],
                item["status"],
                item.get("precondition") or "",
                " | ".join(item.get("steps") or []),
                item.get("expected_result") or "",
            ])
        return StreamingResponse(io.StringIO(output.getvalue()), media_type="text/csv")

    if payload.format == "xlsx":
        wb = Workbook()
        ws = wb.active
        ws.title = "AI_Test_Cases"
        ws.append(["ID", "标题", "类型", "优先级", "状态", "前置条件", "步骤", "预期结果"])
        for item in cases:
            ws.append(
                [
                    item["id"],
                    item["title"],
                    item["case_type"],
                    item["priority"],
                    item["status"],
                    item.get("precondition") or "",
                    "\n".join(item.get("steps") or []),
                    item.get("expected_result") or "",
                ]
            )

        stream = io.BytesIO()
        wb.save(stream)
        stream.seek(0)
        headers = {
            "Content-Disposition": f'attachment; filename="ai-test-design-{payload.design_id}.xlsx"'
        }
        return StreamingResponse(
            stream,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers,
        )

    # markdown default
    lines = ["# AI测试设计-用例导出", ""]
    for idx, item in enumerate(cases, start=1):
        lines.extend(
            [
                f"## {idx}. {item['title']}",
                f"- 类型: {item['case_type']}",
                f"- 优先级: {item['priority']}",
                f"- 状态: {item['status']}",
                f"- 前置条件: {item.get('precondition') or '无'}",
                "- 步骤:",
            ]
        )
        for step in item.get("steps") or []:
            lines.append(f"  - {step}")
        lines.append(f"- 预期结果: {item.get('expected_result') or ''}")
        lines.append("")
    return StreamingResponse(io.StringIO("\n".join(lines)), media_type="text/markdown")


async def _generate_design_summary(db: AsyncSession, knowledge: KnowledgeSource, payload: DesignGenerateRequest) -> dict[str, Any]:
    provider = await get_enabled_provider_by_usage(db, "design")
    if provider and provider.provider_type in {"openai_compatible", "volcengine_ark_coding"}:
        prompt = f"""
你是一名测试设计专家。请输出 JSON，字段必须包含：
function_scope(数组), coverage_dimensions(数组), risks(数组), missing_info(数组)。

需求标题: {knowledge.title}
模块: {knowledge.module_name or ""}
内容:
{knowledge.content}
附加说明:
{knowledge.extra_instruction or ""}
"""
        try:
            output = await call_openai_compatible_json(
                endpoint=provider.endpoint,
                api_key=provider.api_key,
                model_name=payload.model_name or provider.model_name,
                prompt=prompt,
                timeout_s=provider.timeout,
                temperature=provider.temperature,
                max_tokens=provider.max_tokens,
            )
            data = output.get("json")
            if data:
                data["raw_output"] = output.get("text")
                data["model_name"] = payload.model_name or provider.model_name
                data["source"] = "ai"
                data["fallback_reason"] = None
                return data
            log_ai_fallback("invalid_json", output.get("text") or "")
            fallback_reason = "invalid_json"
        except Exception:
            log_ai_fallback("request_failed", f"design generate request failed (knowledge_id={knowledge.id})")
            fallback_reason = "request_failed"
    else:
        log_ai_fallback("provider_unavailable", "design provider missing or unsupported")
        fallback_reason = "provider_unavailable"

    content_head = (knowledge.content or "").split("\n")[0][:40]
    return {
        "function_scope": [knowledge.module_name or "核心流程", content_head or "业务流程"],
        "coverage_dimensions": ["正常流程", "异常流程", "边界值", "权限控制", "状态流转"],
        "risks": ["输入校验遗漏", "边界条件覆盖不足", "状态切换异常"],
        "missing_info": ["未提供更详细的接口字段约束"],
        "raw_output": "fallback-generated",
        "model_name": payload.model_name or "fallback",
        "source": "fallback",
        "fallback_reason": fallback_reason,
    }


async def _generate_points_from_design(db: AsyncSession, design: DesignResult, model_name: Optional[str]) -> dict[str, Any]:
    provider = await get_enabled_provider_by_usage(db, "design")
    if provider and provider.provider_type in {"openai_compatible", "volcengine_ark_coding"}:
        prompt = f"""
根据以下测试设计摘要生成测试点，输出 JSON，格式：
{{"points":[{{"category":"正常流程","content":"...","priority":"P1","selected":true}}]}}

设计摘要:
function_scope: {design.function_scope}
coverage_dimensions: {design.coverage_dimensions}
risks: {design.risks}
missing_info: {design.missing_info}
"""
        try:
            output = await call_openai_compatible_json(
                endpoint=provider.endpoint,
                api_key=provider.api_key,
                model_name=model_name or provider.model_name,
                prompt=prompt,
                timeout_s=provider.timeout,
                temperature=provider.temperature,
                max_tokens=provider.max_tokens,
            )
            parsed = output.get("json") or {}
            points = parsed.get("points")
            if isinstance(points, list) and points:
                valid = []
                for p in points:
                    if not isinstance(p, dict):
                        continue
                    valid.append(
                        {
                            "category": p.get("category") if p.get("category") in CATEGORIES else "其他",
                            "content": str(p.get("content") or "").strip() or "补充测试点",
                            "priority": p.get("priority") if p.get("priority") in {"P0", "P1", "P2", "P3"} else "P1",
                            "selected": bool(p.get("selected", True)),
                        }
                    )
                if valid:
                    return {
                        "points": valid,
                        "source": "ai",
                        "fallback_reason": None,
                        "model_name": model_name or provider.model_name,
                        "raw_output": output.get("text") or "",
                    }
            log_ai_fallback("invalid_json", output.get("text") or "")
            fallback_reason = "invalid_json"
        except Exception:
            log_ai_fallback("request_failed", f"points generate request failed (design_id={design.id})")
            fallback_reason = "request_failed"
    else:
        log_ai_fallback("provider_unavailable", "design provider missing or unsupported")
        fallback_reason = "provider_unavailable"

    fallback: list[dict[str, Any]] = []
    for cat in CATEGORIES[:5]:
        fallback.append(
            {
                "category": cat,
                "content": f"{cat}覆盖：围绕{(design.function_scope or ['目标功能'])[0]}设计关键测试点",
                "priority": "P1",
                "selected": True,
            }
        )
    return {
        "points": fallback,
        "source": "fallback",
        "fallback_reason": fallback_reason,
        "model_name": model_name or "fallback",
        "raw_output": "fallback-generated",
    }


async def _generate_cases_from_points(
    db: AsyncSession,
    design: DesignResult,
    points: list[AITestPoint],
    payload: CaseGenerateRequest,
) -> dict[str, Any]:
    provider = await get_enabled_provider_by_usage(db, "design")
    if provider and provider.provider_type in {"openai_compatible", "volcengine_ark_coding"}:
        prompt_points = [
            {"id": p.id, "category": p.category, "content": p.content, "priority": p.priority}
            for p in points
        ]
        prompt = f"""
你是一名测试工程师。请根据测试点生成结构化测试用例，输出 JSON：
{{"cases":[{{"point_id":1,"title":"...","precondition":"...","steps":["..."],"expected_result":"...","priority":"P1","case_type":"{payload.case_type}","coverage_dimension":"正常流程"}}]}}

设计ID: {design.id}
测试点: {json.dumps(prompt_points, ensure_ascii=False)}
输出数量上限: {payload.output_count}
"""
        try:
            output = await call_openai_compatible_json(
                endpoint=provider.endpoint,
                api_key=provider.api_key,
                model_name=payload.model_name or provider.model_name,
                prompt=prompt,
                timeout_s=provider.timeout,
                temperature=provider.temperature,
                max_tokens=provider.max_tokens,
            )
            parsed = output.get("json") or {}
            cases = parsed.get("cases")
            if isinstance(cases, list) and cases:
                valid = []
                for c in cases[: payload.output_count]:
                    if not isinstance(c, dict):
                        continue
                    steps = c.get("steps")
                    if not isinstance(steps, list):
                        steps = ["执行步骤待补充"]
                    valid.append(
                        {
                            "point_id": c.get("point_id"),
                            "title": str(c.get("title") or "自动生成测试用例"),
                            "precondition": str(c.get("precondition") or ""),
                            "steps": [str(s) for s in steps if str(s).strip()],
                            "expected_result": str(c.get("expected_result") or "结果符合预期"),
                            "priority": c.get("priority") if c.get("priority") in {"P0", "P1", "P2", "P3"} else "P1",
                            "case_type": c.get("case_type") if c.get("case_type") in {"functional", "api", "ui", "generic"} else payload.case_type,
                            "coverage_dimension": str(c.get("coverage_dimension") or ""),
                            "status": "new",
                            "model_name": payload.model_name or provider.model_name,
                            "raw_output": output.get("text"),
                        }
                    )
                if valid:
                    return {
                        "cases": valid,
                        "source": "ai",
                        "fallback_reason": None,
                        "model_name": payload.model_name or provider.model_name,
                        "raw_output": output.get("text") or "",
                    }
            log_ai_fallback("invalid_json", output.get("text") or "")
            fallback_reason = "invalid_json"
        except Exception:
            log_ai_fallback("request_failed", f"cases generate request failed (design_id={design.id})")
            fallback_reason = "request_failed"
    else:
        log_ai_fallback("provider_unavailable", "design provider missing or unsupported")
        fallback_reason = "provider_unavailable"

    generated: list[dict[str, Any]] = []
    for idx, p in enumerate(points[: payload.output_count], start=1):
        generated.append(
            {
                "id": None,
                "point_id": p.id,
                "title": f"[FALLBACK] {p.category}用例-{idx}",
                "precondition": "系统可访问，基础数据已准备",
                "steps": [f"根据测试点执行：{p.content}", "观察系统返回与状态变化"],
                "expected_result": "系统返回符合预期且无异常报错",
                "priority": p.priority,
                "case_type": payload.case_type,
                "coverage_dimension": p.category,
                "status": "new",
                "model_name": payload.model_name or "fallback",
                "raw_output": "fallback-generated",
            }
        )
    return {
        "cases": generated,
        "source": "fallback",
        "fallback_reason": fallback_reason,
        "model_name": payload.model_name or "fallback",
        "raw_output": "fallback-generated",
    }


async def _get_or_404(db: AsyncSession, model_cls, row_id: int, detail: str):
    result = await db.execute(select(model_cls).where(model_cls.id == row_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail=detail)
    return row


def _case_to_dict(r: AITestCase) -> dict[str, Any]:
    return {
        "id": r.id,
        "design_id": r.design_id,
        "point_id": r.point_id,
        "title": r.title,
        "precondition": r.precondition,
        "steps": r.steps or [],
        "expected_result": r.expected_result,
        "case_type": r.case_type,
        "priority": r.priority,
        "coverage_dimension": r.coverage_dimension,
        "status": r.status,
        "model_name": r.model_name,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
    }
