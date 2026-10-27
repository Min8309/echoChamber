"""Bounded official/public sources. Never fetch arbitrary user URLs."""

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

import requests
from fastapi import HTTPException
from app.services import datasets
from app.services.limits import day_and_retry, reject, setting

CATALOG = {
    "khaters": {
        "name": "K-HATERS",
        "source_url": "https://github.com/ssu-humane/K-HATERS",
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "attribution": "Park, Chaewon; Kim, Suhwan; Park, Kyubyong; Park, Kunwoo (2023). K-HATERS: A Hate Speech Detection Corpus in Korean with Target-Specific Ratings. Findings of EMNLP 2023.",
    },
    "kold": {
        "name": "KOLD",
        "source_url": "https://github.com/boychaboy/KOLD",
        "license": "별도 이용 조건 확인 필요",
        "license_url": "https://github.com/boychaboy/KOLD#data",
        "attribution": "Jeong et al. (2022). KOLD: Korean Offensive Language Dataset. EMNLP 2022. 원본 배포자의 이용 조건을 확인하세요.",
    },
    "youtube": {
        "name": "YouTube Data API v3",
        "source_url": "https://developers.google.com/youtube/v3",
        "license": "YouTube API 서비스 약관·개발자 정책 적용",
        "license_url": "https://developers.google.com/youtube/terms/developer-policies",
        "attribution": "Source: YouTube. Collected via YouTube Data API v3. 익명화·선택·편집된 댓글이며 YouTube의 보증이나 사실 확인 결과가 아닙니다.",
    },
}


def signing_key(db):
    db.execute(
        "CREATE TABLE IF NOT EXISTS collection_secret (name TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    with db:
        db.execute(
            "INSERT OR IGNORE INTO collection_secret VALUES ('signing', ?)",
            (secrets.token_hex(32),),
        )
    return (
        db.execute("SELECT value FROM collection_secret WHERE name='signing'")
        .fetchone()[0]
        .encode()
    )


def sign_origin(origin, owner):
    db = datasets.connect()
    try:
        key = signing_key(db)
    finally:
        db.close()
    content = json.dumps(
        {"origin": origin, "owner": owner}, ensure_ascii=False, sort_keys=True
    ).encode()
    encoded = base64.urlsafe_b64encode(content).decode()
    return encoded + "." + hmac.new(key, encoded.encode(), hashlib.sha256).hexdigest()


def verify_origin(token, owner):
    try:
        encoded, signature = token.split(".")
        db = datasets.connect()
        try:
            key = signing_key(db)
        finally:
            db.close()
        if not hmac.compare_digest(
            signature, hmac.new(key, encoded.encode(), hashlib.sha256).hexdigest()
        ):
            raise ValueError
        data = json.loads(base64.urlsafe_b64decode(encoded))
        if data["owner"] != owner or data["origin"]["provider"] not in CATALOG:
            raise ValueError
        if time.time() - data["origin"]["collected_epoch"] > 86400:
            raise HTTPException(
                409, "수집 미리보기가 하루 이상 지났습니다. 다시 수집해 주세요."
            )
        return data["origin"]
    except HTTPException:
        raise
    except (ValueError, KeyError, TypeError):
        raise HTTPException(400, "수집 출처 확인 정보가 올바르지 않습니다.")


def quota(ip=None):
    db = datasets.connect()
    now = time.time()
    day, retry = day_and_retry(now)
    try:
        db.execute("CREATE TABLE IF NOT EXISTS collection_requests (ip TEXT, ts REAL)")
        db.execute(
            "CREATE TABLE IF NOT EXISTS collection_calls (day TEXT PRIMARY KEY, units INTEGER)"
        )
        db.execute("BEGIN IMMEDIATE")
        if ip is not None:
            hashed = hashlib.sha256(ip.encode()).hexdigest()
            db.execute("DELETE FROM collection_requests WHERE ts <= ?", (now - 3600,))
            count = db.execute(
                "SELECT count(*) FROM collection_requests WHERE ip = ?", (hashed,)
            ).fetchone()[0]
            if count >= setting("COLLECTION_REQUESTS_PER_HOUR", 10):
                reject("시간당 외부 자료 수집 한도에 도달했습니다.", 3600)
            db.execute("INSERT INTO collection_requests VALUES (?, ?)", (hashed, now))
        else:
            row = db.execute(
                "SELECT units FROM collection_calls WHERE day = ?", (day,)
            ).fetchone()
            if (row[0] if row else 0) >= setting("COLLECTION_DAILY_CALL_CAP", 200):
                reject("오늘의 외부 자료 API 호출 한도에 도달했습니다.", retry)
            db.execute(
                "INSERT INTO collection_calls VALUES (?, 1) ON CONFLICT(day) DO UPDATE SET units=units+1",
                (day,),
            )
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


class OfficialHTTP:
    def __init__(self):
        self.calls = 0

    def get(self, url, params, key=None):
        if self.calls >= 10:
            raise HTTPException(
                429, "한 번에 최대 10회만 외부 API를 호출합니다. 수집량을 줄여 주세요."
            )
        quota()
        self.calls += 1
        headers = {"Accept": "application/json"}
        if key:
            headers["X-Goog-Api-Key"] = key
        try:
            with requests.get(
                url,
                params=params,
                headers=headers,
                timeout=(5, 20),
                stream=True,
                allow_redirects=False,
            ) as response:
                body = bytearray()
                for chunk in response.iter_content(65536):
                    body.extend(chunk)
                    if len(body) > 2 * 1024 * 1024:
                        raise HTTPException(
                            502, "자료 서버의 응답 크기가 한도를 넘었습니다."
                        )
                try:
                    data = json.loads(body)
                except ValueError:
                    raise HTTPException(
                        502, "공식 자료 서버에서 JSON 응답을 받지 못했습니다."
                    )
                if not isinstance(data, dict):
                    raise HTTPException(502, "자료 서버의 응답 형식이 변경됐습니다.")
                if response.status_code >= 400:
                    reason = (
                        ((data.get("error") or {}).get("errors") or [{}])[0].get(
                            "reason", ""
                        )
                        if isinstance(data.get("error"), dict)
                        else ""
                    )
                    if reason == "commentsDisabled":
                        raise HTTPException(
                            409, "이 영상은 댓글이 비활성화돼 있습니다."
                        )
                    if reason in {"videoNotFound", "notFound"}:
                        raise HTTPException(
                            404, "영상을 찾을 수 없거나 공개 댓글을 조회할 수 없습니다."
                        )
                    if (
                        reason
                        in {"quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded"}
                        or response.status_code == 429
                    ):
                        reject("공식 자료 서버의 호출 한도에 도달했습니다.", 3600)
                    if key and response.status_code in {400, 401, 403}:
                        raise HTTPException(
                            424,
                            "YouTube API 키의 권한·API 활성화·제한 설정을 확인해 주세요.",
                        )
                    raise HTTPException(
                        502,
                        "공식 자료 서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.",
                    )
                if 300 <= response.status_code < 400:
                    raise HTTPException(
                        502,
                        "자료 서버가 다른 주소로 이동했습니다. 연결 설정을 확인해 주세요.",
                    )
                return data
        except requests.RequestException:
            raise HTTPException(
                502,
                "공식 자료 서버 연결이 지연되거나 차단됐습니다. 서버 네트워크 설정을 확인해 주세요.",
            )


def video_id(value):
    value = value.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", value):
        return value
    parsed = urlparse(value if "://" in value else "https://" + value)
    if parsed.scheme not in {"https", "http"} or parsed.username or parsed.password:
        raise HTTPException(
            422, "YouTube 영상 주소 또는 11자리 영상 ID를 입력해 주세요."
        )
    if parsed.hostname in {"youtu.be", "www.youtu.be"}:
        candidate = parsed.path.strip("/")
    elif parsed.hostname in {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com",
    }:
        candidate = (
            parse_qs(parsed.query).get("v", [""])[0]
            if parsed.path == "/watch"
            else parsed.path.strip("/").split("/")[-1]
            if parsed.path.startswith(("/shorts/", "/embed/", "/live/"))
            else ""
        )
    else:
        candidate = ""
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate):
        raise HTTPException(
            422, "YouTube 영상 주소 또는 11자리 영상 ID를 입력해 주세요."
        )
    return candidate


def reference_labels(record):
    result = {}
    for name in ["label", "target_label", "OFF", "TGT", "GRP"]:
        value = record.get(name)
        if value is not None:
            result[name] = (
                json.dumps(value, ensure_ascii=False)
                if not isinstance(value, str)
                else value
            )[:300]
    return result


def normalize(records):
    # Raw source IDs and channel IDs exist only in this function's local maps.
    ids = {str(row["id"]): f"collected-{i + 1}" for i, row in enumerate(records)}
    authors = {}
    rows = []
    for i, record in enumerate(records):
        author = record.get("author")
        if author:
            authors.setdefault(str(author), f"작성자 {len(authors) + 1}")
        rows.append(
            {
                "local_id": ids[str(record["id"])],
                "text": datasets.redact(record["text"]),
                "author": authors.get(str(author), "") if author else "",
                "thread": None,
                "reply_to_id": ids.get(str(record.get("parent"))),
                "rating": None,
                "date": (record.get("date") or "")[:10] or None,
                "reference_labels": reference_labels(record),
                "selected": True,
            }
        )
    return rows


def collect_youtube(request, http):
    key = os.getenv("YOUTUBE_API_KEY") or os.getenv("YOUTUBE_DATA_API_KEY")
    if not key:
        raise HTTPException(
            409,
            "Render 환경 변수 YOUTUBE_API_KEY에 YouTube Data API v3 키를 등록해 주세요. 키는 채팅이나 입력 화면에 붙여 넣지 마세요.",
        )
    vid = video_id(request.video)
    records = []
    page = None
    truncated = False
    warnings = []
    while len(records) < request.limit and http.calls < 10:
        params = {
            "part": "snippet",
            "videoId": vid,
            "maxResults": min(request.limit, 100),
            "order": "time",
            "textFormat": "plainText",
        }
        if page:
            params["pageToken"] = page
        result = http.get(
            "https://www.googleapis.com/youtube/v3/commentThreads", params, key
        )
        items = result.get("items", [])
        for thread in items:
            if len(records) >= request.limit:
                truncated = True
                break
            snippet = thread.get("snippet", {})
            top = snippet.get("topLevelComment", {})
            detail = top.get("snippet", {})
            text = detail.get("textOriginal") or detail.get("textDisplay") or ""
            if not text.strip() or len(text) > 3000 or not top.get("id"):
                warnings.append("빈 댓글 또는 3,000자 초과 댓글은 건너뛰었습니다.")
                continue
            records.append(
                {
                    "id": top["id"],
                    "text": text,
                    "author": detail.get("authorChannelId", {}).get("value"),
                    "date": detail.get("publishedAt"),
                }
            )
            reply_page = None
            if request.include_replies and snippet.get("totalReplyCount", 0):
                while len(records) < request.limit and http.calls < 10:
                    query = {
                        "part": "snippet",
                        "parentId": top["id"],
                        "maxResults": min(100, request.limit - len(records)),
                        "textFormat": "plainText",
                    }
                    if reply_page:
                        query["pageToken"] = reply_page
                    replies = http.get(
                        "https://www.googleapis.com/youtube/v3/comments", query, key
                    )
                    for reply in replies.get("items", []):
                        info = reply.get("snippet", {})
                        body = info.get("textOriginal") or info.get("textDisplay") or ""
                        if body.strip() and len(body) <= 3000 and reply.get("id"):
                            records.append(
                                {
                                    "id": reply["id"],
                                    "text": body,
                                    "parent": top["id"],
                                    "author": info.get("authorChannelId", {}).get(
                                        "value"
                                    ),
                                    "date": info.get("publishedAt"),
                                }
                            )
                            if len(records) >= request.limit:
                                break
                    reply_page = replies.get("nextPageToken")
                    if not reply_page:
                        break
                if reply_page or len(records) >= request.limit or http.calls >= 10:
                    truncated = True
        page = result.get("nextPageToken")
        if not page or not items:
            break
    if page or http.calls >= 10:
        truncated = True
    return records, {
        "video_id": vid,
        "source_url": f"https://www.youtube.com/watch?v={vid}",
        "truncated": truncated,
        "warnings": list(dict.fromkeys(warnings)),
    }


def collect_khaters(request, http):
    meta = http.get(
        "https://datasets-server.huggingface.co/splits",
        {"dataset": "humane-lab/K-HATERS"},
    )
    candidates = [
        item for item in meta.get("splits", []) if item.get("split") == request.split
    ]
    if not candidates:
        raise HTTPException(
            502, "공식 K-HATERS 데이터 분할 정보를 확인하지 못했습니다."
        )
    config = candidates[0].get("config")
    if not isinstance(config, str) or len(config) > 100:
        raise HTTPException(502, "공식 데이터 설정이 변경됐습니다.")
    result = http.get(
        "https://datasets-server.huggingface.co/rows",
        {
            "dataset": "humane-lab/K-HATERS",
            "config": config,
            "split": request.split,
            "offset": request.offset,
            "length": request.limit,
        },
    )
    records = []
    for index, item in enumerate(result.get("rows", [])[: request.limit]):
        row = item.get("row", {})
        text = row.get("text", "")
        if isinstance(text, str) and text.strip() and len(text) <= 3000:
            records.append({**row, "id": str(row.get("id", index)), "text": text})
    return records, {
        "split": request.split,
        "offset": request.offset,
        "dataset": "humane-lab/K-HATERS",
        "truncated": True,
        "warnings": [
            "연구 데이터의 일부 표본입니다. 원본 공격성·표적 라벨은 가십 여부와 다른 주석입니다."
        ],
    }


def collect(request, owner, ip):
    if request.provider == "youtube":
        # Validate configuration before consuming the source collection request quota.
        if not (os.getenv("YOUTUBE_API_KEY") or os.getenv("YOUTUBE_DATA_API_KEY")):
            raise HTTPException(
                409,
                "Render 환경 변수 YOUTUBE_API_KEY를 먼저 등록해 주세요. API 키를 채팅이나 화면에 붙여 넣지 마세요.",
            )
        video_id(request.video)
    quota(ip)
    http = OfficialHTTP()
    records, extra = (
        collect_youtube(request, http)
        if request.provider == "youtube"
        else collect_khaters(request, http)
    )
    if not records:
        raise HTTPException(404, "가져올 수 있는 공개 댓글이 없습니다.")
    now = time.time()
    origin = {
        "provider": request.provider,
        **CATALOG[request.provider],
        **extra,
        "collected_at": datetime.fromtimestamp(now, timezone.utc).isoformat(),
        "collected_epoch": now,
        "requests_used": http.calls,
        "changes": "최대 30건 선택, 작성자·식별자 가명화, 연락처 가림. 저장 전 사용자가 편집할 수 있음.",
    }
    if request.provider == "youtube":
        origin["expires_at"] = now + 29 * 86400
    return {
        "rows": normalize(records),
        "total": len(records),
        "origin": origin,
        "collection_token": sign_origin(origin, owner),
    }
