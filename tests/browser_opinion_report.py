"""Real browser: ten report sections, unavailable data, JSON export and mobile."""

import asyncio
import json

from playwright.async_api import async_playwright, expect
from test_protection import LiveServer


async def check(server):
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
        page = await browser.new_page(viewport={"width": 1280, "height": 900})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.goto(server.base)
        await page.get_by_role("button", name="실제 데이터 비교", exact=False).click()
        await page.get_by_label("실제 댓글·리뷰 직접 입력", exact=True).fill("아마 좋을 것 같아요\n무조건 최고입니다\n다른 의견입니다")
        await page.get_by_role("button", name="직접 입력 미리보기", exact=True).click()
        await page.get_by_label("선택한 문장의 개인정보를 직접 확인했고", exact=False).check()
        await page.get_by_role("button", name="선택한 3건 저장 · 기초 분석").click()
        region = page.get_by_role("region", name="댓글 여론 변형 리포트")
        await expect(region).to_be_visible()
        await expect(region.get_by_role("button", name="AI 원문 비교 포함", exact=False)).to_be_disabled()
        await region.get_by_label("비교할 원문", exact=False).fill("행사 공지 user@example.test")
        await region.get_by_role("button", name="10개 항목 리포트 생성", exact=True).click()
        await expect(region.locator("article")).to_have_count(10)
        await expect(region.locator("article").nth(4)).to_contain_text("미분석")
        await expect(region.locator("article").nth(0)).not_to_contain_text("user@example.test")
        async with page.expect_download() as download_info:
            await region.get_by_role("button", name="10개 항목 JSON 다운로드", exact=True).click()
        download = await download_info.value
        with open(await download.path()) as handle:
            report = json.load(handle)
        assert len(report["sections"]) == 10
        assert report["sections"][3]["result"]["단정"]["댓글 수"] == 1
        await page.set_viewport_size({"width": 390, "height": 844})
        assert await page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert not errors, errors
        assert server.units() == 0
        await browser.close()


if __name__ == "__main__":
    with LiveServer(OPENAI_API_KEY="", ECHOCHAMBER_API_KEY="") as server:
        asyncio.run(check(server))
    print("PASS: ten report sections, source redaction, missing analysis, JSON download, mobile")
