import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect


def check_browser(base_url):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="/usr/bin/chromium", headless=True, args=["--no-sandbox"]
        )
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(base_url)
        expect(
            page.get_by_role("heading", name="EchoChamber : 살아 움직이는 소문 연구실")
        ).to_be_visible()
        expect(page.locator(".agent")).to_have_count(3)
        expect(
            page.get_by_role("heading", name="Smallville Live Environment")
        ).to_be_visible()
        town = page.locator(".interactive-town canvas")
        expect(town).to_be_visible()
        expect(town).to_have_attribute("data-sprites-ready", "true")
        asset = page.request.get(base_url + "/assets/pixel-agents/char_0.png")
        assert asset.ok and asset.headers["content-type"].startswith("image/")
        assert page.request.get(base_url + "/assets/pixel-agents/LICENSE.txt").ok
        assert (
            page.locator(".village-panel").bounding_box()["y"]
            < page.locator(".restored-network").bounding_box()["y"]
        )
        page.get_by_role("button", name="마을 공간 확대").click()
        expect(page.get_by_role("button", name="확대 닫기")).to_be_visible()
        page.get_by_role("button", name="확대 닫기").click()
        page.get_by_role("button", name="Klaus 캐릭터 선택").click()
        expect(page.locator(".resident-detail strong")).to_contain_text("Klaus")
        page.get_by_label("소문의 시작점").fill(
            "브라우저 검증: 토요일 도서관 행사가 열립니다."
        )
        page.get_by_label("전달 단계").fill("3")
        page.locator("button.primary[type=submit]").click()
        expect(
            page.get_by_role("status").filter(has_text="실행 결과가 저장되었습니다")
        ).to_be_visible()
        expect(page.locator(".feed li")).to_have_count(3)
        expect(town).to_have_attribute("data-step", "1")
        page.get_by_role("button", name="일시정지", exact=True).click()
        page.wait_for_timeout(350)
        frozen = page.locator(".village-agents button").evaluate_all(
            "els => els.map(el => el.dataset.position)"
        )
        page.wait_for_timeout(400)
        assert (
            page.locator(".village-agents button").evaluate_all(
                "els => els.map(el => el.dataset.position)"
            )
            == frozen
        )
        page.get_by_role("button", name="계속 재생", exact=True).click()
        page.wait_for_function(
            "before => JSON.stringify([...document.querySelectorAll('.village-agents button')].map(el => el.dataset.position)) !== JSON.stringify(before)",
            arg=frozen,
        )
        assert page.locator(".network path[marker-end]").count() > 0
        first = page.locator(".run-id").inner_text()
        page.reload()
        expect(page.locator(".run-id")).to_have_text(first)
        expect(page.locator(".feed li")).to_have_count(3)
        page.get_by_label("소문의 시작점").fill(
            "두 번째 실험 <script>window.bad=true</script>"
        )
        page.get_by_label("전달 단계").fill("2")
        page.locator("button.primary[type=submit]").click()
        expect(
            page.get_by_role("status").filter(has_text="실행 결과가 저장되었습니다")
        ).to_be_visible()
        expect(page.locator(".feed li")).to_have_count(2)
        assert page.evaluate("window.bad") is None
        page.get_by_role(
            "button",
            name="브라우저 검증: 토요일 도서관 행사가 열립니다. 결과 보기",
            exact=True,
        ).click()
        expect(page.locator(".run-id")).to_have_text(first)
        expect(page.locator(".feed li")).to_have_count(3)
        page.get_by_label("소문의 시작점").fill("토요일 도서관 행사가 열립니다.")
        page.evaluate("window.scrollTo(0, 0)")
        page.screenshot(path="/tmp/echo-react-desktop.png", full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate(
            "document.documentElement.scrollWidth <= window.innerWidth"
        ), "mobile horizontal overflow"
        expect(page.locator("button.primary[type=submit]")).to_be_visible()
        page.screenshot(path="/tmp/echo-react-mobile.png", full_page=True)
        # Real HTTP failure: do not show success or add archive records.
        count = page.locator("tbody tr").count()
        page.route(
            "**/api/runs/stream",
            lambda route: route.fulfill(
                status=502,
                content_type="application/json",
                body=json.dumps({"detail": "테스트용 연결 실패"}),
            ),
        )
        page.locator("button.primary[type=submit]").click()
        expect(page.get_by_role("alert")).to_contain_text("테스트용 연결 실패")
        expect(
            page.get_by_role("status").filter(has_text="실행 결과가 저장되었습니다")
        ).to_have_count(0)
        assert page.locator("tbody tr").count() == count
        assert not errors, errors
        print(
            "PASS: 3 agents, streamed execution, graph, persistence on reload, archive switching, escaped text, mobile layout, and HTTP failure state"
        )
        browser.close()


if __name__ == "__main__":
    import os
    import socket
    import subprocess
    import tempfile
    import time
    from urllib.request import urlopen

    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory() as directory:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        base = f"http://127.0.0.1:{port}"
        env = {
            **os.environ,
            "ECHOCHAMBER_DB_PATH": str(Path(directory) / "browser.sqlite3"),
        }
        env.pop("OPENAI_API_KEY", None)
        env.pop("ECHOCHAMBER_API_KEY", None)
        process = subprocess.Popen(
            [
                str(root / ".venv/bin/python"),
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=root,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            for attempt in range(100):
                try:
                    with urlopen(base + "/health", timeout=0.5) as response:
                        if response.status == 200:
                            break
                except OSError:
                    time.sleep(0.1)
            else:
                raise RuntimeError("Backend did not start")
            check_browser(base)
        finally:
            process.terminate()
            process.wait(timeout=10)
