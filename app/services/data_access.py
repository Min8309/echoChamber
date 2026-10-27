"""Browser capability keys: hash at rest, never put keys in URLs or payloads."""

import re
from fastapi import Header, HTTPException
from app.services.datasets import owner_hash


def optional_owner(x_dataset_key: str | None = Header(default=None)):
    if x_dataset_key is None:
        return None
    if not re.fullmatch(r"[a-f0-9]{64}", x_dataset_key):
        raise HTTPException(401, "이 브라우저의 데이터 접근 키가 올바르지 않습니다.")
    return owner_hash(x_dataset_key)


def require_owner(x_dataset_key: str | None = Header(default=None)):
    owner = optional_owner(x_dataset_key)
    if owner is None:
        raise HTTPException(401, "이 브라우저의 데이터 접근 키가 필요합니다.")
    return owner


from fastapi.routing import APIRoute


class PrivateDataRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def handler(request):
            response = await original(request)
            if request.url.path.startswith("/api/datasets") or request.headers.get(
                "x-dataset-key"
            ):
                response.headers["Cache-Control"] = "no-store"
                response.headers.append("Vary", "X-Dataset-Key")
            return response

        return handler
