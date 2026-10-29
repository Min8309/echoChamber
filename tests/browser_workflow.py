"""Five-step AI workflow, failure recovery and automatic evidence report (fake SDK)."""

import asyncio
from playwright.async_api import async_playwright, expect
from test_protection import LiveServer


async def check(server):
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
        page = await browser.new_page(viewport={"width": 1440, "height": 1000})
        errors, requests = [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("request", lambda request: requests.append(request.url) if request.method == "POST" else None)
        await page.goto(server.base)
        steps = page.get_by_role("navigation", name="댓글 분석 진행 단계")
        sidebar = page.get_by_role("navigation", name="메인 메뉴")
        await expect(sidebar.locator(".workflow-nav")).to_have_text([
            "1실제 댓글 가져오기", "2데이터 수집 · 확인", "3토론 · 시뮬레이션 설정", "4마을에서 분석", "5분석 결과 리포트"])
        await expect(sidebar.locator('[aria-current="step"]')).to_contain_text("실제 댓글 가져오기")
        await expect(sidebar.get_by_role("button", name="분석 결과 리포트", exact=False)).to_be_disabled()
        await expect(sidebar.get_by_role("button", name="데이터 수집 · 확인", exact=False)).to_be_disabled()
        await expect(steps.get_by_role("button", name="분석 결과 리포트", exact=False)).to_be_disabled()
        await expect(page.get_by_role("heading", name="1. 실제 댓글 데이터 가져오기", exact=True)).to_be_visible()
        await page.screenshot(path="/tmp/echo-workflow-import.png", full_page=True)
        await page.get_by_label("실제 댓글·리뷰 직접 입력", exact=True).fill("행사가 열린대요\n아마 좋은 행사일 것 같아요\n일정 확인이 필요해요")
        await page.get_by_role("button", name="직접 입력 미리보기", exact=True).click()
        await expect(page.get_by_role("heading", name="2. 데이터 수집 · 내용 확인", exact=True)).to_be_visible()
        await expect(sidebar.locator('[aria-current="step"]')).to_contain_text("데이터 수집 · 확인")
        await expect(page.get_by_role("button", name="선택한 3건 저장", exact=False)).to_be_disabled()
        await page.get_by_label("선택한 문장의 개인정보를 직접 확인했고", exact=False).check()
        await page.get_by_role("button", name="선택한 3건 저장", exact=False).click()
        await expect(page.get_by_role("heading", name="3. 실제 자료 토론 · 시뮬레이션 설정", exact=True)).to_be_visible()
        await expect(sidebar.locator('[aria-current="step"]')).to_contain_text("토론 · 시뮬레이션 설정")
        await expect(page.locator(".opinion-report")).to_have_count(0)
        await page.get_by_role("button", name="선택한 3건으로 마을 토론 준비", exact=False).click()
        await page.get_by_label("전달 단계", exact=True).fill("3")
        await expect(page.get_by_label("실행 모드", exact=True)).to_have_value("openai")
        await expect(page.locator(".workspace-grid")).to_be_hidden()

        # Failed original-comment analysis must prevent simulation and result publication.
        await page.route("**/api/datasets/*/analyze", lambda route: route.fulfill(
            status=200, content_type="text/event-stream", body='event: error\ndata: {"detail":"테스트 분석 실패"}\n\n'), times=1)
        await page.get_by_role("button", name="마을에서 댓글 AI 분석 시작", exact=False).click()
        await expect(page.get_by_role("alert")).to_contain_text("테스트 분석 실패")
        await expect(steps.get_by_role("button", name="분석 결과 리포트", exact=False)).to_be_disabled()
        assert not any(url.endswith("/api/runs/stream") for url in requests)
        await page.get_by_role("button", name="설정으로 돌아가기", exact=True).click()
        await page.get_by_role("button", name="선택한 3건으로 마을 토론 준비", exact=False).click()
        await page.get_by_label("전달 단계", exact=True).fill("3")
        await page.get_by_role("button", name="마을에서 댓글 AI 분석 시작", exact=False).click()
        await expect(page.get_by_role("heading", name="4. 마을에서 댓글 분석", exact=True)).to_be_visible()
        await expect(sidebar.locator('[aria-current="step"]')).to_contain_text("마을에서 분석")
        await expect(page.get_by_role("heading", name="5. 댓글 분석 결과 리포트", exact=True)).to_be_visible(timeout=20000)
        await expect(page.locator(".workflow-complete")).to_contain_text("원본 댓글 AI 분석 3/3건")
        await expect(sidebar.locator('[aria-current="step"]')).to_contain_text("분석 결과 리포트")
        await expect(page.locator(".opinion-report article")).to_have_count(10)
        await expect(page.locator(".opinion-report article").nth(1)).to_contain_text("도서관 행사 소식")
        await expect(page.locator(".opinion-report article").nth(4)).to_contain_text("100")
        await expect(page.locator(".report-donut")).to_have_attribute("aria-label", "긍정 0%, 중립 100%, 부정 0%")
        await expect(page.get_by_role("region", name="주요 댓글 주장 순위")).to_be_visible()
        ai_request = next(i for i, url in enumerate(requests) if url.endswith("/analyze"))
        simulation_request = next(i for i, url in enumerate(requests) if url.endswith("/api/runs/stream"))
        report_request = next(i for i, url in enumerate(requests) if url.endswith("/opinion-report"))
        assert ai_request < simulation_request < report_request
        assert server.units() == 9, server.units()
        await page.screenshot(path="/tmp/echo-workflow-results.png", full_page=True)
        await sidebar.get_by_role("button", name="토론 · 시뮬레이션 설정", exact=False).click()
        await expect(page.get_by_role("heading", name="3. 실제 자료 토론 · 시뮬레이션 설정", exact=True)).to_be_visible()
        await page.get_by_role("button", name="선택한 3건으로 마을 토론 준비", exact=False).click()
        await expect(page.get_by_role("heading", name="실제 자료 토론 · 시뮬레이션 설정", exact=True)).to_be_visible()
        await steps.get_by_role("button", name="분석 결과 리포트", exact=False).click()
        await expect(page.locator(".opinion-report article")).to_have_count(10)
        await sidebar.get_by_role("button", name="마을 에이전트", exact=False).click()
        await expect(sidebar.locator('[aria-current="step"]')).to_have_count(0)
        await expect(sidebar.get_by_role("button", name="마을 에이전트", exact=False)).to_have_attribute("aria-current", "page")
        await sidebar.get_by_role("button", name="분석 결과 리포트", exact=False).click()
        await expect(page.locator(".opinion-report article")).to_have_count(10)
        await page.set_viewport_size({"width": 390, "height": 844})
        assert await page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert not errors, errors
        await browser.close()


if __name__ == "__main__":
    with LiveServer(FAKE_CREATE_DELAY=".1", FAKE_PARSE_DELAY=".05") as server:
        asyncio.run(check(server))
    print("PASS: five steps, AI analysis before simulation, failure recovery, automatic ten-section report, mobile")
