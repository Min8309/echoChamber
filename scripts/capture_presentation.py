"""Capture presentation screenshots using synthetic comments and a temporary DB."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
from test_protection import LiveServer
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/presentation/assets"
OUT.mkdir(parents=True, exist_ok=True)
with (
    LiveServer(OPENAI_API_KEY="", ECHOCHAMBER_API_KEY="") as server,
    sync_playwright() as p,
):
    browser = p.chromium.launch(
        executable_path="/usr/bin/chromium", args=["--no-sandbox"]
    )
    page = browser.new_page(
        viewport={"width": 1440, "height": 1000}, device_scale_factor=1
    )
    page.goto(server.base)
    expect(page.get_by_role("heading", name="실제 데이터 비교 연구실")).to_be_visible()
    page.screenshot(path=str(OUT / "workflow.png"))
    page.get_by_label("데이터 이름", exact=True).fill("발표용 가상 댓글 · 도서관 행사")
    page.get_by_label("실제 댓글·리뷰 직접 입력", exact=True).fill(
        "토요일 도서관에서 독서 모임이 열린다고 들었어요.\n공지에는 신청 방법이 없는데 확인이 필요해요.\n카페에서도 행사 소식을 안내하면 좋겠어요."
    )
    page.get_by_role("button", name="직접 입력 미리보기", exact=True).click()
    page.get_by_label("선택한 문장의 개인정보를 직접 확인했고", exact=False).check()
    page.get_by_role("button", name="선택한 3건 저장 · 기초 분석").click()
    page.get_by_role("region", name="자료 정렬과 토론 준비").screenshot(
        path=str(OUT / "selection.png")
    )
    page.get_by_label("토론 인원", exact=True).select_option("4")
    page.get_by_role(
        "button", name="선택한 3건으로 마을 토론 준비", exact=False
    ).click()
    page.get_by_label("전달 단계", exact=True).fill("4")
    page.locator("button.primary[type=submit]").click()
    expect(
        page.get_by_role("status").filter(has_text="실행 결과가 저장되었습니다")
    ).to_be_visible()
    expect(page.locator(".interactive-town canvas")).to_have_attribute(
        "data-sprites-ready", "true"
    )
    page.locator(".interactive-town").screenshot(path=str(OUT / "village.png"))
    page.get_by_role("region", name="자료 토론 시각화").screenshot(
        path=str(OUT / "discussion.png")
    )
    page.locator(".network-panel").screenshot(path=str(OUT / "network.png"))
    browser.close()
print("Captured synthetic-data workflow, selection, village, discussion and network.")
