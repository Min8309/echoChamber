from fastapi import (
    APIRouter,
    HTTPException,
)
from openai import OpenAIError
from app.routers.ingestion import messages

from app.models.analysis import (
    DialogueAnalysis,
    DialogueAnalysisRequest,
)
from app.services.analysis import analyze_dialogue


router = APIRouter(
    prefix="/analysis",
    tags=["Analysis"],
)


@router.post(
    "/dialogue",
    response_model=DialogueAnalysis,
)
def analyze_dialogue_endpoint(
    request: DialogueAnalysisRequest,
):
    try:
        return analyze_dialogue(
            text=request.text,
            speaker_name=request.speaker_name,
            listener_name=request.listener_name,
        )

    except OpenAIError as error:
        raise HTTPException(
            status_code=502,
            detail=f"OpenAI API 분석 실패: {error}",
        ) from error

    except RuntimeError as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error
    
@router.post("/messages")
def analyze_messages():
    if not messages:
        raise HTTPException(
            status_code=404,
            detail=(
                "분석할 메시지가 없습니다. "
                "먼저 /ingest/messages로 "
                "메시지를 등록하세요."
            ),
        )

    results = []
    success_count = 0
    failed_count = 0

    for message in messages:
        try:
            analysis_request = (
                DialogueAnalysisRequest(
                    text=message.text,
                    speaker_name=message.author_id,
                )
            )

            analysis = analyze_dialogue(
                analysis_request
            )

            results.append(
                {
                    "message_id": (
                        message.message_id
                    ),
                    "thread_id": (
                        message.thread_id
                    ),
                    "source_type": (
                        message.source_type
                    ),
                    "author_id": (
                        message.author_id
                    ),
                    "reply_to_id": (
                        message.reply_to_id
                    ),
                    "text": message.text,
                    "created_at": (
                        message.created_at
                    ),
                    "analysis": analysis,
                    "error": None,
                }
            )

            success_count += 1

        except Exception as error:
            results.append(
                {
                    "message_id": (
                        message.message_id
                    ),
                    "thread_id": (
                        message.thread_id
                    ),
                    "source_type": (
                        message.source_type
                    ),
                    "author_id": (
                        message.author_id
                    ),
                    "reply_to_id": (
                        message.reply_to_id
                    ),
                    "text": message.text,
                    "created_at": (
                        message.created_at
                    ),
                    "analysis": None,
                    "error": str(error),
                }
            )

            failed_count += 1

    gossip_count = sum(
        1
        for result in results
        if result["analysis"] is not None
        and get_is_gossip(
            result["analysis"]
        )
    )

    return {
        "total_count": len(messages),
        "success_count": success_count,
        "failed_count": failed_count,
        "gossip_count": gossip_count,
        "non_gossip_count": (
            success_count - gossip_count
        ),
        "results": results,
    }


def get_is_gossip(analysis) -> bool:
    if isinstance(analysis, dict):
        return bool(
            analysis.get("is_gossip", False)
        )

    return bool(
        getattr(
            analysis,
            "is_gossip",
            False,
        )
    )