"""Build matching Korean HTML/PPTX from reviewed source notes (python-pptx 1.0.2)."""

from pathlib import Path
import json
import html
import base64
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/presentation"
OUT.mkdir(parents=True, exist_ok=True)
SOURCE_COMMIT = "5b0ffce"
DATE = "2026-10-27"
REPO = "https://github.com/Min8309/echoChamber"
S = [
    dict(
        tag="ECHOCHAMBER / PROJECT & ENGINEERING",
        title="실제 목소리를,\n가상 마을에서 실험하다",
        lead="실제 댓글·리뷰 → 자료 선별 → 3~4인 토론 → 대화 흐름 시각화",
        cards=[
            (
                "핵심 주제",
                "실제 텍스트와 가상 대화를 같은 기준으로 비교하는 AI 실험 도구",
            ),
            ("구현 기반", "React · FastAPI · SQLite · OpenAI · Canvas"),
            ("발표 기준", "현재 구현 코드 검토본 · 2026.10.27"),
        ],
        notes="EchoChamber는 실제 여론을 예측하거나 사실을 판정하는 도구가 아니다. 수집 자료와 가상 대화의 차이를 관찰하는 작은 연구 워크벤치다.",
    ),
    dict(
        tag="01 / CORE QUESTION",
        title="어떤 정보가, 누구의 대화에서 달라지는가?",
        lead="원문과 시뮬레이션을 연결해 관찰 가능한 실험으로 만든다.",
        cards=[
            ("자료", "YouTube 공개 댓글·답글, K-HATERS 표본, 사용자가 제공한 리뷰"),
            ("관찰", "인물별 발언과 이번 참고 자료, 대화 단계, AI 감정·확실성 분류"),
            ("결과", "선택한 원문과 가상 발화의 수치·관계망·히스토리 비교"),
        ],
        refs=["frontend/src/RealDataLab.jsx", "frontend/src/DiscussionResults.jsx"],
        notes="혐오 주석 데이터는 공격성에 관한 참고 라벨이다. 가십 여부나 사실성의 정답으로 취급하지 않는다.",
    ),
    dict(
        tag="02 / USER JOURNEY",
        title="수집에서 시각화까지, 한 흐름으로",
        lead="기존 마을 디자인을 유지하고 실제 데이터를 첫 화면에 배치했다.",
        pipeline=[
            "01 수집·가져오기",
            "02 익명화·저장",
            "03 정렬·최대 10건 선택",
            "04 3~4인 토론",
            "05 분석·비교·다운로드",
        ],
        cards=[
            (
                "수집 30건 / 토론 10건",
                "미리보기 후 확인한 자료만 저장하고, 선택 순서대로 토론 자료를 고정한다.",
            ),
            (
                "단계 1~20회",
                "묶음 토론은 단계 수가 자료 수와 참여 인원 이상이어야 한다.",
            ),
        ],
        refs=[
            "frontend/src/main.jsx",
            "frontend/src/RealDataLab.jsx",
            "app/routers/workbench.py",
        ],
        notes="한 번에 수집·저장하는 자료 수와 토론에 선택하는 자료 수는 다르다. 묶음 토론에는 모든 인물과 자료가 최소 한 번 배정된다.",
    ),
    dict(
        tag="03 / REAL DATA WORKSPACE",
        title="실제 자료를 먼저 정리한다",
        lead="정렬·검색·선별 후, 자료 묶음을 마을로 전달한다.",
        image="selection.png",
        cards=[
            ("정렬", "수집 순서 · 긴 문장 · AI 부정 감정 · 높은 별점"),
            ("선별", "문장 검색과 체크박스 / 최대 10건"),
            ("모드 선택", "3명 또는 4명 / 4번째 인물은 실행 전용 가상 자료 검토자"),
        ],
        refs=["frontend/src/RealDataLab.jsx"],
        notes="AI 부정 감정 정렬은 이미 도착한 분석에만 의존한다. 검색은 기존 선택을 해제하지 않는다. 화면 예시는 합성 문장이다.",
    ),
    dict(
        tag="04 / ARCHITECTURE",
        title="화면·실행·분석·저장을 분리한 구조",
        lead="FastAPI가 React 정적 빌드와 API를 같은 Origin에서 제공한다.",
        pipeline=[
            "React / Vite",
            "FastAPI / Pydantic",
            "Simulation + Analysis",
            "SQLite / Snapshots",
        ],
        cards=[
            (
                "외부 입력",
                "YouTube Data API v3 · Hugging Face 데이터 뷰어 · 브라우저 파일 읽기",
            ),
            (
                "실시간 경로",
                "POST /api/runs/stream → SSE 이벤트 → React 상태 → Canvas·말풍선",
            ),
            ("영속화 경로", "완료 실행만 트랜잭션 저장 → 접근 키로 비공개 실행 조회"),
        ],
        refs=[
            "Dockerfile",
            "app/main.py",
            "app/routers/workbench.py",
            "app/services/runs.py",
        ],
        notes="GitHub Pages만으로 FastAPI를 실행할 수 없다. 실제 서비스는 Render Docker 배포를 사용한다. SQLite를 쓰는 현재 범위는 소규모 데모다.",
    ),
    dict(
        tag="05 / COLLECTION",
        title="공식 API와 연구 파일을 구분해 연결한다",
        lead="자유로운 URL 크롤링 대신 고정된 수집 경로와 작은 호출 한도를 사용한다.",
        cards=[
            (
                "YouTube 공식 API",
                "commentThreads.list + comments.list / 실제 부모-답글 관계 유지 / 서버 전용 YOUTUBE_API_KEY",
            ),
            (
                "K-HATERS",
                "humane-lab/K-HATERS / splits·rows 조회 / CC BY 4.0 출처·변경 표시",
            ),
            (
                "KOLD 파일 가져오기",
                "공식 JSON/JSONL을 사용자가 확보 / 원본 주석자 ID 제거 / 서버 자동 재배포 없음",
            ),
        ],
        refs=[
            "app/services/collection.py",
            "app/routers/collection.py",
            "frontend/src/researchImport.mjs",
        ],
        notes="공식 API라고 모든 재사용이 허용되는 것은 아니다. YouTube 정책·자료 이용 권한을 확인해야 한다. KOLD의 별도 재배포 허용 범위를 확인하지 못해 자동 수집하지 않는다.",
    ),
    dict(
        tag="06 / DATA & PRIVACY",
        title="자료·대화·분석을 연결하는 데이터 계약",
        lead="브라우저에서 가림 처리하고 서버에서도 다시 정리한다.",
        cards=[
            (
                "DatasetRow",
                "text · author · reply_to_id · rating · date · reference_labels",
            ),
            (
                "Source snapshot",
                "선택한 row_id·text·analysis·origin을 실행 당시 자료로 보존",
            ),
            (
                "Run / Event",
                "speaker_id · listener_id · utterance · discussion_stage · source_row_ids · analysis",
            ),
        ],
        code="X-Dataset-Key: <브라우저 생성 64자리 hex>\n→ 서버에는 owner hash 저장\n→ dataset과 연결 run은 owner로 조회\n→ source_data.rows에 선택 자료 스냅샷",
        refs=[
            "app/routers/datasets.py",
            "app/services/datasets.py",
            "app/services/data_access.py",
        ],
        notes="브라우저 접근 키는 계정 인증·암호화 저장을 대신하지 않는다. 저장소를 지우면 접근 복구가 안 된다. 사람 이름·주소 등 자동 마스킹이 놓치는 정보는 사용자 검토가 필요하다.",
    ),
    dict(
        tag="07 / DISCUSSION ENGINE",
        title="인물과 자료를 번갈아 배정한다",
        lead="자료 요약 → 근거 점검 → 다른 관점 → 종합 정리",
        code='speaker = roster[(step - 1) % len(roster)]\nlistener = roster[step % len(roster)]\nevidence = source["rows"][(step - 1) % len(source["rows"])]\n\n# OpenAI 입력: 전체 선택 자료 + 최근 4개 발언\n# 단계마다 대화 생성 1회 + 구조화 분석 1회',
        cards=[
            (
                "OpenAI 모드",
                "인물 성향과 단계 과제를 제공하고 이전 발언에 반응하도록 생성",
            ),
            (
                "규칙 모드",
                "자료 인용·확인 필요 문구의 템플릿 / AI 토론으로 표시하지 않음",
            ),
        ],
        refs=["app/routers/workbench.py"],
        notes="이는 실행 가능한 알고리즘의 발췌다. 실제 대화는 자료 속 지시를 따르지 않도록 시스템 지시를 둔다. 자료 배정은 근거 인용 정확도를 자동 검증했다는 뜻이 아니다.",
    ),
    dict(
        tag="08 / SSE",
        title="발화를 먼저 보여주고, 분석을 나중에 합친다",
        lead="토큰 스트리밍이 아니라 완성된 발화 단위의 SSE다.",
        pipeline=["start", "step", "analysis", "… 반복 …", "complete / error"],
        cards=[
            ("start / step", "실행·인물 초기화 → 대화와 관계망 갱신"),
            ("analysis", "같은 단계 말풍선에 감정·확실성·평판 영향 병합"),
            (
                "complete / error",
                "성공한 실행 저장 / 실패·중단 시 부분 실행 저장하지 않음",
            ),
        ],
        refs=[
            "app/routers/workbench.py",
            "frontend/src/main.jsx",
            "frontend/src/components/Lab.jsx",
        ],
        notes="클라이언트가 연결을 끊은 시점에 이미 서버 저장이 완료됐을 수 있다. 히스토리로 완료 여부를 다시 확인한다. SDK는 일반 응답을 받고 이를 발화 이벤트로 전달한다.",
    ),
    dict(
        tag="09 / PIXEL VILLAGE",
        title="실제 발언 기록이 마을의 움직임이 된다",
        lead="Canvas·프레임 루프·BFS 경로 탐색을 대화 단계와 동기화한다.",
        image="village.png",
        cards=[
            ("24 × 18 타일", "카페 · 도서관 · 광장 / 장애물을 피하는 4방향 경로"),
            ("발언자 → 청자", "두 인물의 만남·말풍선·현재 단계 표시"),
            ("출처 고지", "Pixel Agents 이식 코드·스프라이트: MIT 고지 유지"),
        ],
        refs=[
            "frontend/src/VillageScene.jsx",
            "frontend/src/village/town.js",
            "frontend/src/village/pixel-agents/pathfinding.js",
            "frontend/public/assets/pixel-agents/LICENSE.txt",
        ],
        notes="마을은 임의의 배경 동영상이 아니다. 저장된 speaker/listener와 event.step을 이용해 이동 경로를 만든다. 캡처는 합성 자료와 규칙 모드다.",
    ),
    dict(
        tag="10 / VISUAL ANALYSIS",
        title="참여·자료 배정·변화를 수치로 보여준다",
        lead="대화 타임라인과 관계망을 함께 읽는다.",
        image="discussion.png",
        cards=[
            ("참여", "인물별 발언 횟수 / AI 분석 완료 수"),
            ("범위", "검토 자료 배정 수 / 선택 자료 수"),
            ("흐름", "단계별 신뢰도·문자열 변화 / AI 감정 분포"),
        ],
        refs=["frontend/src/DiscussionResults.jsx", "frontend/src/Comparison.jsx"],
        notes="화면의 AI 감정은 규칙 모드에서 비어 있다. 이를 0% 감정으로 조작하지 않는다. 자료 배정 수는 실제 의미 이해나 정확한 인용의 증명이 아니다.",
    ),
    dict(
        tag="11 / ANALYSIS CONTRACT",
        title="기초 통계와 AI 의미 분류를 구분한다",
        lead="같은 분석 함수·모델·버전일 때만 AI 수치를 직접 비교한다.",
        cards=[
            ("기초 지표", "표본 수 · 평균 글자 수 · 질문·전언 표현 비율 / 문자열 규칙"),
            (
                "AI 의미 분류",
                "가십 · 감정 · 확실성 · 평판 영향 / DialogueAnalysis 구조화 응답",
            ),
            (
                "해석의 경계",
                "신뢰도는 성향 기반 감쇠 / 변화율은 문자열 차이 / 외부 사실 검증 아님",
            ),
        ],
        code='ANALYSIS_VERSION = "text-v1"\nclient.responses.parse(\n    model=analysis_model(),\n    text_format=DialogueAnalysis, ...\n)',
        refs=[
            "app/services/text_analysis.py",
            "app/models/analysis.py",
            "app/routers/datasets.py",
        ],
        notes="묶음 토론에서는 선택한 원문만 비교 분모에 넣는다. 공격성 참고 라벨은 가십의 정답과 다르다. 문자열 변화에는 서로 다른 자료를 다루는 데 따른 주제 차이도 들어간다.",
    ),
    dict(
        tag="12 / COST & SAFETY",
        title="작은 공개 데모를 위한 사용량·접근 보호",
        lead="요청 횟수와 실제 SDK 시도를 별도로 제한한다.",
        cards=[
            (
                "LLM 예산",
                "IP당 시간당 10요청 / 서버 UTC 일일 100 SDK 시도 기본값 / 토큰·금액 한도 아님",
            ),
            ("수집 예산", "시간당 10요청 / 일일 외부 HTTP 200회 / 수집당 최대 10회"),
            (
                "접근·수명",
                "비공개 자료와 연결 실험 owner 조회 / YouTube 자료 29일 만료·연결 실험 삭제",
            ),
        ],
        refs=[
            "app/services/limits.py",
            "app/services/ai_client.py",
            "app/services/collection.py",
            "app/services/datasets.py",
        ],
        notes="DEMO_READ_ONLY는 에이전트·기억·메시지 직접 추가를 차단한다. 실험 결과 저장까지 막지 않는다. 자동 가림·로컬 접근 키는 완전한 개인정보 보호나 계정 권한 시스템을 보장하지 않는다.",
    ),
    dict(
        tag="13 / CODE MAP",
        title="핵심 코드와 책임",
        lead="프로젝트를 설명할 때 바로 열어볼 구현 위치",
        cards=[
            (
                "화면·선별",
                "main.jsx: SSE·화면 전환 / RealDataLab.jsx: 정렬·선택·비교·내보내기",
            ),
            (
                "실행·분석",
                "workbench.py: 자료 확인·인물 배정·생성·분석·저장 / text_analysis.py: 공통 분류 계약",
            ),
            (
                "수집·보호",
                "collection.py: 고정 공급자·출처 서명·쿼터 / data_access.py: owner 경계",
            ),
            (
                "시각화·저장",
                "DiscussionResults.jsx: 지표·차트 / VillageScene.jsx: 마을 / runs.py·datasets.py: SQLite",
            ),
        ],
        refs=[
            "frontend/src/main.jsx",
            "frontend/src/RealDataLab.jsx",
            "app/routers/workbench.py",
            "app/services/collection.py",
            "frontend/src/DiscussionResults.jsx",
            "app/services/runs.py",
        ],
        notes="HTML 각 장의 코드 링크는 검토한 커밋에 고정한다. 구현과 설명을 함께 검토할 수 있게 상세 노트와 원본 생성 스크립트를 저장소에 포함한다.",
    ),
    dict(
        tag="14 / VERIFICATION",
        title="확인한 것과 아직 보장하지 않는 것",
        lead="동작 검증과 모델 성능 검증을 구분한다.",
        cards=[
            ("자동 검증", "서버 테스트 34개 · Node 테스트 10개 / 임시 DB·HTTP·모의 AI"),
            (
                "브라우저 검증",
                "선별 → 4인 실행 → SSE → 그래프 → 비교 / 모바일·기존 기능 회귀",
            ),
            (
                "실서비스 확인",
                "K-HATERS 실제 수집·저장·4인 규칙 실행·비공개 비교·테스트 자료 삭제",
            ),
            (
                "한계",
                "실제 OpenAI 응답 품질·유튜브 키 유효성·분류 정확도·대규모 부하를 검증한 수치가 아님",
            ),
        ],
        refs=[
            "tests/test_discussion.py",
            "tests/browser_discussion.py",
            "tests/test_protection.py",
            "tests/test_collection.py",
        ],
        notes="34개 서버 테스트와 10개 Node 테스트는 현재 코드 검증 범위다. UI 스크린샷은 합성 자료로 촬영했다. 실제 AI 모드는 테스트 대역으로 경로와 호출 수를 확인했으며 모델 정확도 평가가 아니다.",
    ),
    dict(
        tag="15 / DEMO & NEXT",
        title="데모는 작은 자료 묶음 하나로",
        lead="실험의 출처·설정·결과를 함께 설명한다.",
        pipeline=[
            "자료 3건 저장",
            "정렬·선택",
            "3~4명 / 4~8단계",
            "대화·자료 배정 확인",
            "비교·다운로드",
        ],
        cards=[
            (
                "필수 설정",
                "수집: YOUTUBE_API_KEY / AI: OPENAI_API_KEY 또는 ECHOCHAMBER_API_KEY / 선택: 영속 SQLite 경로",
            ),
            (
                "현재 다운로드",
                "CSV: 실제 자료 행 / JSON·HTML: 분석과 선택한 비교 수치 / .ppt·.pptx: 이 발표 자료",
            ),
            (
                "다음 확장 제안",
                "명시적 계정 권한 · 사람 평가셋 · 출처 인용 검증 · 토큰/비용 예산 · PostgreSQL / 작업 큐",
            ),
        ],
        refs=[".env.example", "render.yaml", "app/services/research_report.py"],
        notes="다음 확장은 현재 구현과 구분한 제안이다. 무료 인스턴스의 로컬 SQLite는 재배포 때 소실될 수 있어 영속 디스크가 필요하다. 실제 AI 대화는 서버 키 설정 후 선택한다.",
    ),
]

# Small shared helpers keep the PPTX editable: text and shapes, not slide screenshots.
prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BG = "F7F9FD"
INK = "14233F"
BLUE = "3366CC"
TEAL = "0D9488"
GRAY = "62738C"


def rect(slide, x, y, w, h, color, rounded=False):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE,
        Inches(x),
        Inches(y),
        Inches(w),
        Inches(h),
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor.from_string(color)
    shape.line.fill.background()
    return shape


def txt(slide, x, y, w, h, text, size=20, color=INK, bold=False):
    tf = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)).text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.02)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    for i, line in enumerate(text.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.font.name = "Noto Sans CJK KR"
        p.font.size = Pt(size)
        p.font.bold = bold
        p.font.color.rgb = RGBColor.from_string(color)
        p.space_after = Pt(6)
    return tf


def picture(slide, name, x, y, w, h):
    path = OUT / "assets" / name
    iw, ih = Image.open(path).size
    scale = min(w / iw, h / ih)
    slide.shapes.add_picture(
        str(path),
        Inches(x + (w - iw * scale) / 2),
        Inches(y + (h - ih * scale) / 2),
        width=Inches(iw * scale),
        height=Inches(ih * scale),
    )


for idx, d in enumerate(S):
    sl = prs.slides.add_slide(prs.slide_layouts[6])
    sl.background.fill.solid()
    sl.background.fill.fore_color.rgb = RGBColor.from_string(BG)
    rect(sl, 0, 0, 0.12, 7.5, BLUE)
    txt(sl, 0.55, 0.32, 12, 0.3, d["tag"], 11, BLUE, True)
    title_size = 36 if idx == 0 else 29
    txt(
        sl,
        0.55,
        0.85,
        12,
        1.35 if idx == 0 else 0.65,
        d["title"],
        title_size,
        INK,
        True,
    )
    txt(sl, 0.55, 2.25 if idx == 0 else 1.65, 12, 0.65, d["lead"], 17, GRAY)
    top = 3.15 if idx == 0 else 2.55
    if d.get("image"):
        rect(sl, 0.55, top, 7.4, 4.0, "FFFFFF", True)
        picture(sl, d["image"], 0.65, top + 0.05, 7.2, 3.9)
        for j, (a, b) in enumerate(d["cards"]):
            y = top + j * 1.3
            txt(sl, 8.25, y, 4.35, 0.4, a, 19, BLUE, True)
            txt(sl, 8.25, y + 0.45, 4.35, 0.72, b, 15, GRAY)
    elif d.get("code"):
        rect(sl, 0.55, top, 7.7, 3.8, "14233F", True)
        tf = txt(sl, 0.8, top + 0.25, 7.2, 3.35, d["code"], 14, "E4ECFA")
        for p in tf.paragraphs:
            p.font.name = "Noto Sans Mono CJK KR"
        for j, (a, b) in enumerate(d["cards"]):
            y = top + j * 1.25
            txt(sl, 8.5, y, 4.15, 0.35, a, 18, BLUE, True)
            txt(sl, 8.5, y + 0.4, 4.15, 0.8, b, 14, GRAY)
    else:
        if d.get("pipeline"):
            steps = d["pipeline"]
            width = 12.15 / len(steps)
            for j, label in enumerate(steps):
                rect(
                    sl,
                    0.55 + j * width,
                    top,
                    width - 0.12,
                    0.8,
                    BLUE if j % 2 == 0 else TEAL,
                    True,
                )
                txt(
                    sl,
                    0.65 + j * width,
                    top + 0.16,
                    width - 0.32,
                    0.5,
                    label,
                    14,
                    "FFFFFF",
                    True,
                )
            top += 1.15
        cards = d["cards"]
        gap = 0.18
        # Two columns for four entries; three horizontal cards otherwise.
        cols = 2 if len(cards) == 4 else len(cards)
        cw = (12.2 - gap * (cols - 1)) / cols
        ch = 1.65 if len(cards) == 4 else 2.55
        for j, (a, b) in enumerate(cards):
            x = 0.55 + (j % cols) * (cw + gap)
            y = top + (j // cols) * (ch + 0.18)
            rect(sl, x, y, cw, ch, "FFFFFF", True)
            txt(sl, x + 0.2, y + 0.2, cw - 0.4, 0.45, a, 20, BLUE, True)
            txt(sl, x + 0.2, y + 0.8, cw - 0.4, ch - 0.95, b, 17, GRAY)
    refs = d.get("refs", [])
    if refs:
        txt(sl, 0.55, 6.82, 11.7, 0.24, "CODE  " + "  ·  ".join(refs[:2]), 9, GRAY)
    txt(
        sl,
        0.55,
        7.15,
        11.8,
        0.2,
        f"EchoChamber  /  SOURCE {SOURCE_COMMIT}  /  {DATE}  /  화면: 합성 자료·규칙 모드",
        8,
        GRAY,
    )
    txt(sl, 12.1, 7.1, 0.7, 0.25, f"{idx + 1:02d} / {len(S):02d}", 10, BLUE, True)
    sl.notes_slide.notes_text_frame.text = (
        d["notes"]
        + "\n\n검토 코드:\n"
        + "\n".join(REPO + "/blob/" + SOURCE_COMMIT + "/" + r for r in refs)
    )
prs.core_properties.title = "EchoChamber — 실제 데이터와 가상 마을 토론"
prs.core_properties.subject = "프로젝트 핵심 주제·구조·코드·검증 범위"
prs.core_properties.author = "EchoChamber project"
prs.core_properties.keywords = "React, FastAPI, SQLite, SSE, OpenAI, Pixel Agents"
prs.save(OUT / "EchoChamber.pptx")

esc = html.escape


def image_uri(name):
    return (
        "data:image/png;base64,"
        + base64.b64encode((OUT / "assets" / name).read_bytes()).decode()
    )


sections = []
for idx, d in enumerate(S):
    flow = ""
    if d.get("pipeline"):
        flow = (
            '<ol class="flow">'
            + "".join("<li>" + esc(s) + "</li>" for s in d["pipeline"])
            + "</ol>"
        )
    cards = (
        '<div class="cards">'
        + "".join(
            "<article><h3>" + esc(a) + "</h3><p>" + esc(b) + "</p></article>"
            for a, b in d["cards"]
        )
        + "</div>"
    )
    content = cards
    if d.get("image"):
        content = (
            '<div class="visual"><figure><img src="'
            + image_uri(d["image"])
            + '" alt="'
            + esc(d["title"])
            + ' — 합성 자료·규칙 모드 화면"><figcaption>합성 댓글을 사용한 로컬 화면 · AI 응답 품질을 나타내지 않음</figcaption></figure>'
            + cards
            + "</div>"
        )
    if d.get("code"):
        content = (
            '<div class="visual"><pre><code>'
            + esc(d["code"])
            + "</code></pre>"
            + cards
            + "</div>"
        )
    refs = (
        '<div class="refs">'
        + "".join(
            '<a href="'
            + REPO
            + "/blob/"
            + SOURCE_COMMIT
            + "/"
            + esc(r)
            + '" target="_blank" rel="noreferrer">'
            + esc(r)
            + "</a>"
            for r in d.get("refs", [])
        )
        + "</div>"
    )
    sections.append(
        f'<section class="slide" id="slide-{idx + 1}" aria-label="{idx + 1}. {esc(d["title"])}"><div class="tag">{esc(d["tag"])}</div><h1>{esc(d["title"]).replace(chr(10), "<br>")}</h1><p class="lead">{esc(d["lead"])}</p>{flow}{content}<details><summary>발표자 노트 · 해석 범위</summary><p>{esc(d["notes"])}</p></details>{refs}<footer>SOURCE {SOURCE_COMMIT} · {DATE}<span>{idx + 1:02d} / {len(S):02d}</span></footer></section>'
    )
css = """*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:72px}body{margin:0;background:#eaf0f8;color:#14233f;font-family:"Noto Sans CJK KR","Malgun Gothic",sans-serif}nav{position:sticky;top:0;z-index:10;background:#14233f;color:white;display:flex;align-items:center;gap:10px;padding:14px 24px;flex-wrap:wrap}nav strong{margin-right:auto}nav a,nav button{color:inherit;background:transparent;border:1px solid #7187aa;border-radius:6px;padding:8px 12px;text-decoration:none;font:inherit;font-size:12px;cursor:pointer}.slide{position:relative;min-height:720px;max-width:1280px;margin:28px auto;padding:46px 48px 35px;background:#f7f9fd;border-left:8px solid #3366cc;border-radius:8px;box-shadow:0 8px 30px #14233f0d;scroll-margin-top:0}.tag{color:#3366cc;font-size:12px;letter-spacing:2px;font-weight:bold}h1{font-size:36px;line-height:1.35;margin:24px 0 16px}h3{font-size:20px;color:#3366cc;margin:0 0 14px}.lead{font-size:19px;color:#62738c;line-height:1.7;margin-bottom:30px}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:18px}article{background:white;padding:24px;border:1px solid #e1e8f2;border-radius:10px}article p{line-height:1.8;color:#526680;margin:0}.flow{list-style:none;padding:0;display:flex;gap:10px;margin:24px 0}.flow li{flex:1;background:#3366cc;color:white;padding:18px 12px;font-size:14px;border-radius:8px}.flow li:nth-child(even){background:#0d9488}.visual{display:grid;grid-template-columns:minmax(0,1.6fr) minmax(260px,1fr);gap:24px}.visual .cards{grid-template-columns:1fr}.visual figure{margin:0;background:white;padding:12px;border-radius:10px;display:flex;flex-direction:column;justify-content:center}.visual img{display:block;width:100%;max-height:490px;object-fit:contain}.visual figcaption{font-size:11px;color:#62738c;text-align:center;margin-top:10px}pre{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.9;color:#e4ecfa;background:#14233f;border-radius:10px;padding:24px;margin:0;font-size:14px}details{margin-top:25px;font-size:13px;color:#526680;line-height:1.8}summary{cursor:pointer;color:#3366cc}.refs{display:flex;gap:10px;flex-wrap:wrap;font-size:11px;margin-top:20px}.refs a{color:#42658a;overflow-wrap:anywhere}footer{display:flex;justify-content:space-between;font-size:10px;color:#62738c;margin-top:25px;border-top:1px solid #e1e8f2;padding-top:14px}footer span{color:#3366cc;font-weight:bold}@media(max-width:760px){.slide{margin:14px 10px;padding:28px 20px;min-height:0}h1{font-size:27px}.visual{grid-template-columns:1fr}.flow{flex-direction:column}nav{padding:12px}.lead{font-size:16px}.cards{grid-template-columns:1fr}}@media print{@page{size:landscape;margin:10mm}body{background:white}nav{display:none}.slide{margin:0;border-radius:0;box-shadow:none;min-height:0;page-break-after:always;break-after:page;padding:16px 22px;max-width:none}h1{font-size:28px}.lead{font-size:14px}.visual img{max-height:310px}article{padding:14px}article p{font-size:12px}h3{font-size:16px}.flow li{padding:12px;font-size:11px}details{display:none}.refs{font-size:8px}footer{margin-top:12px}*{-webkit-print-color-adjust:exact;print-color-adjust:exact}}"""
js = """const slides=[...document.querySelectorAll('.slide')];function move(direction){const index=slides.reduce((best,slide,i)=>Math.abs(slide.getBoundingClientRect().top-80)<Math.abs(slides[best].getBoundingClientRect().top-80)?i:best,0);slides[Math.max(0,Math.min(slides.length-1,index+direction))].scrollIntoView({behavior:'smooth'});}document.querySelector('#prev').onclick=()=>move(-1);document.querySelector('#next').onclick=()=>move(1);document.querySelector('#print').onclick=()=>window.print();document.addEventListener('keydown',event=>{if(event.target.closest('button,a,summary'))return;if(event.key==='ArrowRight'||event.key==='PageDown'){event.preventDefault();move(1);}if(event.key==='ArrowLeft'||event.key==='PageUp'){event.preventDefault();move(-1);}});"""
page = (
    f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>EchoChamber · 프로젝트와 기술 발표</title><meta name="description" content="실제 댓글 수집과 3~4인 가상 마을 토론의 핵심 기술·코드·검증 범위"><style>{css}</style></head><body><nav aria-label="발표 제어"><strong>EchoChamber / Technical Deck</strong><button id="prev">← 이전</button><button id="next">다음 →</button><button id="print">인쇄 / PDF</button><a href="EchoChamber.pptx" download>PPTX</a><a href="EchoChamber.ppt" download>PPT</a><a href="{REPO}">GitHub</a></nav>'
    + "".join(sections)
    + f"<script>{js}</script></body></html>"
)
(OUT / "index.html").write_text(page, encoding="utf-8")
(OUT / "slides.json").write_text(
    json.dumps(
        {
            "source_commit": SOURCE_COMMIT,
            "review_date": DATE,
            "screenshots": "Synthetic comments; rules mode; temporary local database.",
            "slides": S,
        },
        ensure_ascii=False,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
print(f"Built {len(S)} editable PPTX slides and matching HTML.")
