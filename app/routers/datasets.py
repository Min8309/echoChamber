import json
from datetime import date as CalendarDate
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator
from starlette.concurrency import run_in_threadpool

from app.services import datasets, runs
from app.services.ai_client import get_ai_client
from app.services.data_access import require_owner, PrivateDataRoute
from app.services.limits import consume_request
from app.services.text_analysis import ANALYSIS_VERSION, analysis_model, analyze_text

router = APIRouter(
    prefix="/api/datasets", tags=["Real data research"], route_class=PrivateDataRoute
)


class DatasetRow(BaseModel):
    local_id: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=3000)
    author: str = Field(default="", max_length=100)
    thread: str | None = Field(default=None, max_length=100)
    reply_to_id: str | None = Field(default=None, max_length=100)
    rating: float | None = Field(default=None, ge=0, le=5)
    date: CalendarDate | None = None


class DatasetCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    source: Literal["comment", "review"]
    reviewed: Literal[True]
    rows: list[DatasetRow] = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def valid_rows(self):
        if not self.title.strip() or any(not row.text.strip() for row in self.rows):
            raise ValueError("제목과 분석할 내용을 입력해 주세요.")
        if len({row.local_id for row in self.rows}) != len(self.rows):
            raise ValueError("중복된 행 식별자입니다.")
        if any(row.local_id == row.reply_to_id for row in self.rows):
            raise ValueError("자신을 답글 대상으로 지정할 수 없습니다.")
        return self


@router.post("", status_code=201)
def create(request: DatasetCreate, owner=Depends(require_owner)):
    return describe(datasets.create(request, owner))


def describe(data):
    result = datasets.public(data)
    result["basic"] = datasets.basic_stats([row["text"] for row in data["rows"]])
    result["ai"] = datasets.ai_stats(
        [row.get("analysis") for row in data["rows"]], len(data["rows"])
    )
    result["reply_pairs"] = sum(
        row.get("reply_to_id") is not None for row in data["rows"]
    )
    return result


@router.get("")
def listing(owner=Depends(require_owner)):
    return datasets.listing(owner)


@router.get("/{dataset_id}")
def detail(dataset_id: str, owner=Depends(require_owner)):
    return describe(datasets.load(dataset_id, owner))


@router.delete("/{dataset_id}", status_code=204)
def delete(dataset_id: str, owner=Depends(require_owner)):
    datasets.delete(dataset_id, owner)


async def analysis_guard(
    dataset_id: str, request: Request, owner=Depends(require_owner)
):
    data = await run_in_threadpool(datasets.load, dataset_id, owner)
    if any(row.get("analysis") is None for row in data["rows"]):
        await run_in_threadpool(
            consume_request, request.client.host if request.client else "unknown", 1
        )


@router.post("/{dataset_id}/analyze", dependencies=[Depends(analysis_guard)])
async def analyze(dataset_id: str, connection: Request, owner=Depends(require_owner)):
    data = await run_in_threadpool(datasets.load, dataset_id, owner)
    incomplete = any(row.get("analysis") is None for row in data["rows"])
    try:
        client = get_ai_client() if incomplete else None
    except ValueError as error:
        raise HTTPException(409, str(error)) from error

    def checkpoints():
        attempted = set()
        yield "start", describe(datasets.load(dataset_id, owner))
        while client:
            row = datasets.claim(dataset_id, owner, attempted)
            if row is None:
                break
            attempted.add(row["row_id"])
            try:
                analysis = analyze_text(
                    row["text"], row["author"], client=client
                ).model_dump(mode="json")
                datasets.finish(
                    dataset_id,
                    owner,
                    row,
                    analysis=analysis,
                    model=analysis_model(),
                    version=ANALYSIS_VERSION,
                )
                yield "row", describe(datasets.load(dataset_id, owner))
            except HTTPException as error:
                datasets.finish(
                    dataset_id,
                    owner,
                    row,
                    error="호출 한도에 도달했습니다. 완료된 행은 저장됐습니다.",
                )
                raise error
            except Exception:
                datasets.finish(
                    dataset_id,
                    owner,
                    row,
                    error="AI 분석에 실패했습니다. 이 행은 다시 시도할 수 있습니다.",
                )
                yield "row", describe(datasets.load(dataset_id, owner))
        yield "complete", describe(datasets.load(dataset_id, owner))

    iterator = checkpoints()

    async def events():
        try:
            while not await connection.is_disconnected():
                item = await run_in_threadpool(next, iterator, None)
                if item is None or await connection.is_disconnected():
                    break
                kind, payload = item
                yield f"event: {kind}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
        except HTTPException as error:
            payload = {
                "detail": error.detail,
                "status": error.status_code,
                "retry_after": (error.headers or {}).get("Retry-After"),
            }
            yield f"event: error\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
        except Exception:
            yield 'event: error\ndata: {"detail":"분석 연결이 종료됐습니다. 저장된 결과를 다시 불러와 주세요."}\n\n'
        finally:
            iterator.close()
            if client:
                client.close()

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{dataset_id}/compare")
def compare(dataset_id: str, run_id: str, owner=Depends(require_owner)):
    data = datasets.load(dataset_id, owner)
    run = runs.get_run(run_id, owner)
    if run is None:
        raise HTTPException(404, "비교할 실행 기록이 없습니다.")
    real = datasets.ai_stats(
        [row.get("analysis") for row in data["rows"]], len(data["rows"])
    )
    virtual = datasets.ai_stats(
        [event.get("analysis") for event in run["events"]], len(run["events"])
    )
    versions = {
        (row.get("analysis_version"), row.get("analysis_model"))
        for row in data["rows"]
        if row.get("analysis")
    }
    comparable = (
        real["analysed"] == real["total"] > 0
        and virtual["analysed"] == virtual["total"] > 0
        and versions == {(run.get("analysis_version"), run.get("analysis_model"))}
    )
    return {
        "dataset_id": dataset_id,
        "run_id": run_id,
        "title": data["title"],
        "topic": run["topic"],
        "basic": {
            "real": datasets.basic_stats([row["text"] for row in data["rows"]]),
            "virtual": datasets.basic_stats(
                [event["utterance"] for event in run["events"]]
            ),
        },
        "ai": {"real": real, "virtual": virtual, "comparable": comparable},
        "reply_pairs": sum(row.get("reply_to_id") is not None for row in data["rows"]),
        "note": "기초 지표는 동일한 문자열 규칙입니다. AI 수치 비교는 양쪽 분석이 완료되고 모델·분석 버전이 같을 때만 제공합니다. 독립 댓글의 실제 전달 경로나 왜곡·인과관계는 추정하지 않습니다.",
    }


@router.get("/{dataset_id}/export")
def export(
    dataset_id: str,
    format: Literal["csv", "json", "html"] = "json",
    completed_only: bool = False,
    run_id: str | None = None,
    owner=Depends(require_owner),
):
    import csv
    import io
    from datetime import datetime, timezone
    from fastapi.responses import Response

    data = datasets.load(dataset_id, owner)
    headers = {
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
        "Content-Disposition": f'attachment; filename="echochamber-analysis.{format}"',
    }
    rows = [
        row
        for row in data["rows"]
        if row.get("analysis") is not None or not completed_only
    ]
    if not rows:
        raise HTTPException(
            409, "AI 분석이 완료된 행이 없습니다. 전체 행 내보내기를 선택해 주세요."
        )
    report = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "total_dataset_rows": len(data["rows"]),
        "completed_only": completed_only,
        "dataset": describe({**data, "rows": rows}),
        "comparison": compare(dataset_id, run_id, owner) if run_id else None,
        "notice": "미분석·실패 항목은 status로 구분합니다. AI 분류는 사실 확인 결과가 아닙니다.",
    }
    if format == "json":
        return Response(
            json.dumps(report, ensure_ascii=False, indent=2),
            media_type="application/json",
            headers=headers,
        )
    if format == "html":
        from app.services.research_report import html_report

        return Response(html_report(report), media_type="text/html", headers=headers)
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    columns = [
        "number",
        "text",
        "author",
        "rating",
        "date",
        "status",
        "is_gossip",
        "subject",
        "claim",
        "sentiment",
        "certainty",
        "confidence",
        "reputation_impact",
        "reason",
        "analysis_model",
        "analysis_version",
    ]
    writer.writerow(columns)

    def safe(value):
        # CSV quoting alone does not prevent spreadsheet formula execution.
        import re

        if isinstance(value, str) and (
            re.match(r"^\s*[=+\-@]", value) or value.startswith(("\t", "\r", "\n"))
        ):
            return "'" + value
        return value

    for row in rows:
        flat = {**row, **(row.get("analysis") or {})}
        writer.writerow([safe(flat.get(column, "")) for column in columns])
    return Response(
        output.getvalue().encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers=headers,
    )
