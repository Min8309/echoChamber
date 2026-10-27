"""Run with .venv/bin/python tests/browser_protection.py (system Chromium)."""

import asyncio
from playwright.async_api import async_playwright, expect
from test_protection import LiveServer


async def check(server):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path="/usr/bin/chromium", headless=True, args=["--no-sandbox"]
        )
        page = await browser.new_page(viewport={"width": 1440, "height": 1050})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))

        async def delayed_agents(route):
            await asyncio.sleep(5.3)
            await route.continue_()

        await page.route("**/api/agents", delayed_agents)
        await page.goto(server.base, wait_until="domcontentloaded")
        await page.get_by_role("button", name="대시보드", exact=False).click()
        await expect(
            page.get_by_text(
                "첫 접속에는 무료 서버가 깨어나는 시간이 걸릴 수 있습니다.", exact=False
            )
        ).to_be_visible(timeout=5000)
        await expect(page.locator(".agent")).to_have_count(3, timeout=10000)
        await page.unroute("**/api/agents", delayed_agents)
        await page.get_by_label("대화 방식").select_option("autonomous")
        await expect(page.get_by_label("소문의 시작점")).to_be_disabled()
        await page.get_by_label("실행 모드").select_option("openai")
        await page.get_by_label("전달 단계").fill("8")
        await page.locator("button.primary[type=submit]").click()
        await expect(page.get_by_label("대화 방식")).to_be_disabled()
        await expect(page.get_by_text("분석 중…", exact=True)).to_be_visible()
        await expect(page.get_by_label("1단계 분석")).to_contain_text("가십")
        await expect(page.get_by_label("1단계 분석")).to_contain_text("평판 영향 -0.10")
        await page.locator(".feed").evaluate(
            "el => { el.style.maxHeight='180px'; el.style.minHeight='180px'; }"
        )
        await expect(page.locator(".feed li")).to_have_count(3, timeout=10000)
        await page.locator(".feed").evaluate(
            "el => { el.scrollTop=0; el.dispatchEvent(new Event('scroll')); }"
        )
        await expect(page.locator(".feed li").nth(4)).to_be_attached(timeout=10000)
        assert await page.locator(".feed").evaluate("el => el.scrollTop") == 0
        await expect(
            page.get_by_role("status").filter(has_text="실행 결과가 저장되었습니다")
        ).to_be_visible(timeout=15000)
        assert len(server.get("/api/runs").json()) == 1
        assert server.units() == 16

        # Abort during an in-flight analysis; no remaining turns or partial save.
        await page.get_by_label("전달 단계").fill("10")
        await page.locator("button.primary[type=submit]").click()
        await expect(page.get_by_text("분석 중…", exact=True)).to_be_visible()
        await page.get_by_role("button", name="중단", exact=True).click()
        await expect(
            page.get_by_role("status").filter(has_text="중단을 요청했습니다")
        ).to_be_visible()
        await expect(page.get_by_label("대화 방식")).to_be_enabled()
        await asyncio.sleep(0.9)
        assert len(server.get("/api/runs").json()) == 1
        assert server.units() <= 18

        # A real HTTP 429 response drives disabled retry + countdown.
        async def limited(route):
            await route.fulfill(
                status=429,
                headers={"Content-Type": "application/json", "Retry-After": "2"},
                body='{"detail":"테스트 호출 한도"}',
            )

        await page.route("**/api/runs/stream", limited)
        await page.get_by_label("전달 단계").fill("1")
        await page.locator("button.primary[type=submit]").click()
        await expect(page.get_by_role("alert")).to_contain_text("테스트 호출 한도")
        await expect(page.get_by_role("alert").get_by_role("button")).to_be_disabled()
        await expect(page.get_by_role("alert").get_by_role("button")).to_be_enabled(
            timeout=5000
        )
        await page.unroute("**/api/runs/stream", limited)
        await page.get_by_role("button", name="다시 시도", exact=True).click()
        await expect(
            page.get_by_role("status").filter(has_text="실행 결과가 저장되었습니다")
        ).to_be_visible(timeout=10000)
        assert len(server.get("/api/runs").json()) == 2
        assert not errors, errors
        print(
            "PASS: slow startup, autonomous mode, input lock, pending/merged analysis, scroll preservation, abort, HTTP 429 countdown and retry"
        )
        await browser.close()


async def check_legacy_collector(server):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path="/usr/bin/chromium", headless=True, args=["--no-sandbox"]
        )
        page = await browser.new_page()
        # This check targets the local ingestion flow, not external CDN styling.
        await page.route(
            "https://cdn.tailwindcss.com/**",
            lambda route: route.fulfill(
                content_type="application/javascript", body="window.tailwind = {};"
            ),
        )
        await page.goto(server.base + "/real-lab", wait_until="domcontentloaded")
        async with page.expect_response("**/ingest/messages") as result:
            await page.locator("#input-file-csv").set_input_files(
                {
                    "name": "test.csv",
                    "mimeType": "text/csv",
                    "buffer": "text\n도서관 행사\n".encode(),
                }
            )
        response = await result.value
        assert response.status == 403
        body = response.request.post_data_json
        assert body["messages"][0]["source_type"] == "naver_comment"
        assert body["messages"][0]["author_id"] and body["messages"][0]["thread_id"]
        await expect(page.locator("#toast-container")).to_contain_text("읽기 전용")
        await expect(page.locator("#toast-container")).not_to_contain_text(
            "분석이 완료"
        )
        print(
            "PASS: legacy CSV collection uses /ingest/messages with required fields and shows real HTTP 403"
        )
        await browser.close()


if __name__ == "__main__":
    with LiveServer(FAKE_CREATE_DELAY=".1", FAKE_PARSE_DELAY=".6") as server:
        asyncio.run(check(server))

    with LiveServer(DEMO_READ_ONLY="true") as server:
        asyncio.run(check_legacy_collector(server))
