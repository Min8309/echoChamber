"""Real browser: redacted upload → resumable AI → private village → exports."""

import asyncio
import csv
import io
import json
from pathlib import Path
import tempfile

from playwright.async_api import async_playwright, expect
from test_protection import LiveServer

CSV = 'message_id,author_id,text,rating\na,original-author,"카페가 좋나요? test@example.test 010-1234-5678",4\nb,original-author,"아마 서비스가 좋아요, 다시 방문할게요",5\nc,other,"=1+1 <script>window.bad=1</script>",3\n'


async def check(server):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path="/usr/bin/chromium", headless=True, args=["--no-sandbox"]
        )
        page = await browser.new_page(
            viewport={"width": 1440, "height": 1050}, accept_downloads=True
        )
        errors = []
        uploads = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "request",
            lambda request: (
                uploads.append(request.post_data_json)
                if request.method == "POST" and request.url.endswith("/api/datasets")
                else None
            ),
        )
        await page.goto(server.base)
        await expect(
            page.get_by_role("heading", name="1. 실제 댓글 데이터 가져오기", exact=True)
        ).to_be_visible()
        await page.get_by_role("button", name="실제 데이터 비교", exact=False).click()
        await expect(
            page.get_by_role("heading", name="1. 실제 댓글 데이터 가져오기", exact=True)
        ).to_be_visible()
        await page.get_by_label("데이터 이름", exact=True).fill("카페 리뷰 <연구>")
        await page.get_by_label("데이터 종류", exact=True).select_option("review")
        await page.get_by_label("댓글·리뷰 CSV 파일").set_input_files(
            {"name": "reviews.csv", "mimeType": "text/csv", "buffer": CSV.encode()}
        )
        await expect(page.get_by_label("1행 익명화 내용")).to_contain_text("[이메일]")
        assert (
            "test@example.test"
            not in await page.get_by_label("1행 익명화 내용").input_value()
        )
        assert uploads == []
        save = page.get_by_role("button", name="선택한 3건 저장 · 토론 설정으로 →")
        await expect(save).to_be_disabled()
        await page.get_by_label(
            "선택한 문장의 개인정보를 직접 확인했고", exact=False
        ).check()
        await save.click()
        await expect(
            page.get_by_role("heading", name="3. 실제 자료 토론 · 시뮬레이션 설정")
        ).to_be_visible()
        serialized = json.dumps(uploads, ensure_ascii=False)
        assert (
            "original-author" not in serialized
            and "test@example.test" not in serialized
            and "010-1234-5678" not in serialized
        )
        await (
            page.locator(".research-row-results article")
            .first.get_by_role("button", name="이 문장으로 마을 실험", exact=False)
            .click()
        )
        await expect(page.locator(".source-seed")).to_be_visible()
        await expect(page.get_by_label("소문의 시작점")).to_be_disabled()
        await page.get_by_label("전달 단계", exact=True).fill("2")
        await page.get_by_label("실행 모드", exact=True).select_option("openai")
        await page.locator("button.primary[type=submit]").click()
        await expect(page.get_by_role("heading", name="5. 댓글 분석 결과 리포트", exact=True)).to_be_visible(timeout=15000)
        await expect(page.locator(".opinion-report article")).to_have_count(10)
        assert server.units() == 7
        run_id = await page.get_by_label("비교할 가상 실행", exact=True).input_value()
        assert server.get("/api/runs/" + run_id).status_code == 404
        await expect(page.get_by_label("비교할 가상 실행", exact=True)).to_have_value(run_id)
        await page.get_by_role("button", name="그래프·숫자로 비교", exact=True).click()
        await expect(
            page.locator(".research-comparison .comparison-metric")
        ).to_have_count(7)
        with tempfile.TemporaryDirectory() as directory:
            for format in ["csv", "json", "html"]:
                await page.get_by_label("다운로드 형식", exact=True).select_option(
                    format
                )
                async with page.expect_download() as result:
                    await page.get_by_role(
                        "button", name="분석 결과 다운로드", exact=True
                    ).click()
                download = await result.value
                assert download.suggested_filename.endswith("." + format)
                target = Path(directory) / ("result." + format)
                await download.save_as(target)
                content = target.read_text(encoding="utf-8-sig")
                if format == "csv":
                    rows = list(csv.DictReader(io.StringIO(content)))
                    assert len(rows) == 3 and rows[2]["text"].startswith("'=")
                elif format == "json":
                    report = json.loads(content)
                    assert (
                        report["comparison"]["run_id"] == run_id
                        and report["dataset"]["ai"]["analysed"] == 3
                    )
                else:
                    assert (
                        "<script>" not in content
                        and "&lt;script&gt;" in content
                        and 'class="track"' in content
                    )
        await page.set_viewport_size({"width": 390, "height": 844})
        assert await page.evaluate(
            "document.documentElement.scrollWidth<=innerWidth"
        ), "research mobile overflow"
        await page.screenshot(path="/tmp/echo-research-mobile.png", full_page=True)
        await page.set_viewport_size({"width": 1440, "height": 1050})
        await page.evaluate("window.scrollTo(0,0)")
        await page.screenshot(path="/tmp/echo-research-desktop.png", full_page=True)
        page.on("dialog", lambda dialog: dialog.accept())
        await page.get_by_role("button", name="데이터 삭제", exact=True).click()
        await expect(
            page.get_by_role("status").filter(
                has_text="데이터와 연결 실험을 삭제했습니다"
            )
        ).to_be_visible()
        await page.get_by_role("button", name="대시보드", exact=False).click()
        await expect(page.locator(".source-seed")).to_have_count(0)
        await expect(page.locator(".run-id")).to_have_count(0)
        assert not errors, errors
        print(
            "PASS: local redaction/review, automatic AI analysis, private village, comparison graphs, CSV/JSON/HTML downloads, mobile and linked-data deletion"
        )
        await browser.close()


async def check_no_ai(server):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path="/usr/bin/chromium", headless=True, args=["--no-sandbox"]
        )
        page = await browser.new_page(accept_downloads=True)
        await page.goto(server.base)
        await page.get_by_role("button", name="실제 데이터 비교", exact=False).click()
        await page.get_by_label("실제 댓글·리뷰 직접 입력", exact=True).fill("카페가 좋아요. test@example.test\n서비스가 좋나요?\n아마 다시 방문할 것 같아요")
        await page.get_by_role("button", name="직접 입력 미리보기", exact=True).click()
        await expect(page.get_by_label("1행 익명화 내용")).to_contain_text("[이메일]")
        await page.get_by_label(
            "선택한 문장의 개인정보를 직접 확인했고", exact=False
        ).check()
        await page.get_by_role("button", name="선택한 3건 저장 · 토론 설정으로 →").click()
        await (
            page.locator(".research-row-results article")
            .first.get_by_role("button", name="이 문장으로 마을 실험", exact=False)
            .click()
        )
        await page.get_by_label("전달 단계", exact=True).fill("1")
        await page.locator("button.primary[type=submit]").click()
        await expect(page.get_by_role("heading", name="5. 댓글 분석 결과 리포트", exact=True)).to_be_visible()
        await expect(
            page.get_by_role("button", name="AI 분석 / 이어서 분석", exact=False)
        ).to_be_disabled()
        await page.get_by_label("AI 완료 행만", exact=True).check()
        await expect(
            page.get_by_role("button", name="분석 결과 다운로드", exact=True)
        ).to_be_disabled()
        await page.get_by_label("AI 완료 행만", exact=True).uncheck()
        for format in ["csv", "json", "html"]:
            await page.get_by_label("다운로드 형식", exact=True).select_option(format)
            async with page.expect_download() as result:
                await page.get_by_role(
                    "button", name="분석 결과 다운로드", exact=True
                ).click()
            assert (await result.value).suggested_filename.endswith("." + format)
        await page.get_by_role("button", name="그래프·숫자로 비교", exact=True).click()
        await expect(page.locator(".research-comparison .comparison-metric")).to_have_count(4)
        assert server.units() == 0
        print(
            "PASS: no API key + read-only demo still supports owned CSV import, basic analysis, all downloads, private rules village and basic graph comparison"
        )
        await browser.close()


if __name__ == "__main__":
    with LiveServer(FAKE_PARSE_DELAY=".6") as server:
        asyncio.run(check(server))

    with LiveServer(
        DEMO_READ_ONLY="true", ECHOCHAMBER_API_KEY="", OPENAI_API_KEY=""
    ) as server:
        asyncio.run(check_no_ai(server))
