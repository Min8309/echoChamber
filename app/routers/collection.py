import os
from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field, model_validator

from app.services import collection
from app.services.data_access import require_owner, PrivateDataRoute

router = APIRouter(
    prefix="/api/collection",
    tags=["Official comment collection"],
    route_class=PrivateDataRoute,
)


class CollectRequest(BaseModel):
    provider: Literal["youtube", "khaters"]
    video: str = Field(default="", max_length=500)
    limit: int = Field(default=20, ge=1, le=30)
    include_replies: bool = True
    split: Literal["train", "validation", "test"] = "test"
    offset: int = Field(default=0, ge=0, le=190000)

    @model_validator(mode="after")
    def require_video(self):
        if self.provider == "youtube" and not self.video.strip():
            raise ValueError("YouTube 영상 주소를 입력해 주세요.")
        return self


@router.get("/sources")
def sources():
    return {
        "youtube_configured": bool(
            os.getenv("YOUTUBE_API_KEY") or os.getenv("YOUTUBE_DATA_API_KEY")
        ),
        "sources": collection.CATALOG,
        "limits": {"rows": 30, "requests_per_collection": 10},
    }


@router.post("/preview")
def preview(request: CollectRequest, connection: Request, owner=Depends(require_owner)):
    return collection.collect(
        request, owner, connection.client.host if connection.client else "unknown"
    )
