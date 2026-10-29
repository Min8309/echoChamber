"""Browser: sorted real evidence → four people → streamed flow → charts."""

import asyncio
from playwright.async_api import async_playwright, expect
from test_protection import LiveServer


async def check(server):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path="/usr/bin/chromium", args=["--no-sandbox"]
        )
        page = await browser.new_page(viewport={"width": 1440, "height": 1050})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.goto(server.base)
        await page.get_by_role("button", name="실제 데이터 비교", exact=False).click()
        await page.get_by_label("실제 댓글·리뷰 직접 입력", exact=True).fill(
            "짧은 의견\n두 번째 자료는 조금 더 긴 의견입니다\n세 번째 정보가 맞는지 확인하고 싶어요"
        )
        await page.get_by_role("button", name="직접 입력 미리보기", exact=True).click()
        await page.get_by_label(
            "선택한 문장의 개인정보를 직접 확인했고", exact=False
        ).check()
        await page.get_by_role("button", name="선택한 3건 저장 · 기초 분석").click()
        await page.get_by_label("정보 정렬", exact=True).select_option("length")
        await expect(
            page.locator(".research-row-results article").first
        ).to_contain_text("두 번째 자료")
        await page.get_by_label("1행 토론 자료 선택", exact=True).uncheck()
        await page.get_by_label("토론 인원", exact=True).select_option("4")
        await page.get_by_role(
            "button", name="선택한 2건으로 마을 토론 준비", exact=False
        ).click()
        await expect(
            page.get_by_text("2건의 자료 · 4인 토론", exact=True)
        ).to_be_visible()
        await page.get_by_label("전달 단계", exact=True).fill("4")
        await page.locator("button.primary[type=submit]").click()
        await expect(
            page.get_by_role("status").filter(has_text="실행 결과가 저장되었습니다")
        ).to_be_visible()
        await expect(
            page.get_by_role("region", name="자료 토론 시각화")
        ).to_be_visible()
        await expect(
            page.locator(".discussion-stat-grid article").nth(0)
        ).to_contain_text("4명")
        await expect(
            page.locator(".discussion-stat-grid article").nth(1)
        ).to_contain_text("2/2건")
        await expect(page.locator(".feed .discussion-stage")).to_have_count(4)
        await expect(page.locator(".interactive-town canvas")).to_have_attribute(
            "data-sprites-ready", "true"
        )
        await page.screenshot(path="/tmp/echo-discussion-desktop.png", full_page=True)
        await page.set_viewport_size({"width": 390, "height": 844})
        assert await page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        await page.get_by_role(
            "button", name="실제 데이터 · 결과 비교로 돌아가기", exact=False
        ).click()
        await page.get_by_role("button", name="그래프·숫자로 비교", exact=True).click()
        await expect(
            page.locator(".research-comparison .comparison-metric").first
        ).to_contain_text("2건")
        assert not errors, errors
        assert server.units() == 0
        await browser.close()


if __name__ == "__main__":
    with LiveServer(OPENAI_API_KEY="", ECHOCHAMBER_API_KEY="") as server:
        asyncio.run(check(server))
    print(
        "PASS: sort/select real evidence, four-person village, coverage, flow charts, private comparison, mobile"
    )
