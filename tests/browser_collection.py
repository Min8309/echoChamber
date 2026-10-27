"""Exercise the source collector UI against a synthetic official API fixture."""
import asyncio
from playwright.async_api import async_playwright, expect
from test_protection import LiveServer

async def check(server):
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
        page = await browser.new_page()
        await page.goto(server.base)
        await page.get_by_role('button', name='실제 데이터 비교', exact=False).click()
        await page.get_by_role('button', name='공식 자료 수집 · 미리보기').click()
        await expect(page.get_by_label('1행 익명화 내용')).to_be_visible()
        await expect(page.locator('.source-attribution').first).to_contain_text('CC BY 4.0')
        await page.get_by_label('선택한 문장의 개인정보를 직접 확인했고', exact=False).check()
        await page.get_by_role('button', name='선택한 3건 저장 · 기초 분석').click()
        await expect(page.get_by_role('heading', name='2. 분석 결과 · 이어서 분석 · 다운로드')).to_be_visible()
        await page.get_by_label('댓글 수집 경로').select_option('youtube')
        await page.get_by_label('YouTube 영상 주소').fill('https://youtu.be/abcdefghijk')
        await page.get_by_role('button', name='공식 자료 수집 · 미리보기').click()
        await expect(page.get_by_label('1행 익명화 내용')).to_contain_text('[이메일]')
        await browser.close()

if __name__ == '__main__':
    with LiveServer(FAKE_COLLECTION='true', YOUTUBE_API_KEY='test-only-source-key') as server:
        asyncio.run(check(server))
    print('PASS: K-HATERS collection, source attribution, reviewed save and YouTube anonymous preview')
