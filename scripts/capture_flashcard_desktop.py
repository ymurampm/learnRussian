import asyncio
import sys
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 850})
        page = await context.new_page()
        await page.goto('http://localhost:8085')
        await page.wait_for_timeout(2000)

        # Start Salon Flashcard
        await page.evaluate('window.SalonFlashcard.startSession(6)')
        await page.wait_for_timeout(1200)

        # 1. Capture Front Face
        await page.screenshot(path='C:/Users/ymura/.gemini/antigravity/brain/bbc31de0-69a0-4783-bff1-27960b90b96c/desktop_flashcard_front.png')

        # 2. Flip to Back Face
        await page.keyboard.press('Space')
        await page.wait_for_timeout(600)

        # Scroll to bottom to inspect Tanya bubble and rating buttons
        await page.evaluate('document.querySelector(".flash-card-box").scrollTop = 500')
        await page.wait_for_timeout(400)
        await page.screenshot(path='C:/Users/ymura/.gemini/antigravity/brain/bbc31de0-69a0-4783-bff1-27960b90b96c/desktop_flashcard_back_scrolled.png')
        print("Captured scrolled back face successfully")

        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
