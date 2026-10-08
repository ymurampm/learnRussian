import asyncio
import sys
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding='utf-8')

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('http://localhost:8085')
        await page.wait_for_timeout(2000)

        # 1. Trigger Salon Flashcard
        await page.evaluate('window.SalonFlashcard.startSession(4)')
        await page.wait_for_timeout(1500)

        # Take screenshot of front face
        await page.screenshot(path='C:/Users/ymura/.gemini/antigravity/brain/bbc31de0-69a0-4783-bff1-27960b90b96c/screenshot_flashcard_front.png')
        print('Front face loaded successfully')

        # 2. Test Micro-Hint (H key)
        await page.keyboard.press('h')
        await page.wait_for_timeout(500)
        stem_box_visible = await page.evaluate('document.getElementById("flashStemHintBox").style.display !== "none"')
        print('Stem hint visible after H:', stem_box_visible)

        # Test Acoustic Priming (A key)
        await page.keyboard.press('a')
        await page.wait_for_timeout(500)
        badge_text = await page.evaluate('document.getElementById("flashAcousticBadgeContainer").innerText')
        print('Acoustic badge text:', badge_text)

        await page.screenshot(path='C:/Users/ymura/.gemini/antigravity/brain/bbc31de0-69a0-4783-bff1-27960b90b96c/screenshot_flashcard_hints.png')

        # 3. Flip Card (Space key)
        await page.keyboard.press('Space')
        await page.wait_for_timeout(500)
        is_flipped = await page.evaluate('window.SalonFlashcard.isFlipped')
        print('Card is flipped:', is_flipped)

        # 4. Test Recitation (C key)
        await page.keyboard.press('c')
        await page.wait_for_timeout(500)
        is_reciting = await page.evaluate('window.SalonFlashcard.isReciting')
        print('Is reciting after C:', is_reciting)
        recite_banner = await page.evaluate('document.getElementById("flashReciteLiveBannerContainer").innerText')
        print('Recite banner:', recite_banner)
        await page.screenshot(path='C:/Users/ymura/.gemini/antigravity/brain/bbc31de0-69a0-4783-bff1-27960b90b96c/screenshot_flashcard_reciting.png')

        # Stop recitation with second C
        await page.keyboard.press('c')
        await page.wait_for_timeout(300)
        is_reciting_after = await page.evaluate('window.SalonFlashcard.isReciting')
        print('Is reciting stopped after second C:', not is_reciting_after)

        # 5. Test Fermaata evaluation
        # Artificially set start time 16 seconds ago
        await page.evaluate('window.SalonFlashcard.cardStartTime = Date.now() - 16000')
        await page.keyboard.press('2') # rate with 2
        await page.wait_for_timeout(600)
        fermaata_toast = await page.evaluate('document.querySelector(".fermaata-toast-banner") !== null')
        print('Fermaata toast appeared:', fermaata_toast)
        await page.screenshot(path='C:/Users/ymura/.gemini/antigravity/brain/bbc31de0-69a0-4783-bff1-27960b90b96c/screenshot_flashcard_fermaata.png')

        # Complete session
        while not await page.evaluate('window.SalonFlashcard.isComplete'):
            await page.keyboard.press('Space')
            await page.wait_for_timeout(200)
            await page.keyboard.press('3')
            await page.wait_for_timeout(300)

        await page.wait_for_timeout(1000)
        tanya_quote = await page.evaluate('document.querySelector(".tanya-tea-quote").innerText')
        print('Tanya personal echo quote sample:', tanya_quote[:100] + '...')
        intimacy_reward = await page.evaluate('document.querySelector(".tea-intimacy-reward") !== null')
        print('Intimacy reward banner displayed:', intimacy_reward)
        await page.screenshot(path='C:/Users/ymura/.gemini/antigravity/brain/bbc31de0-69a0-4783-bff1-27960b90b96c/screenshot_flashcard_completion.png')

        # 6. Close modal & check Dashboard Encore
        await page.keyboard.press('Escape')
        await page.wait_for_timeout(1000)
        encore_card = await page.evaluate('document.querySelector(".salon-encore-card") !== null')
        print('Dashboard encore card exists on dashboard:', encore_card)
        await page.screenshot(path='C:/Users/ymura/.gemini/antigravity/brain/bbc31de0-69a0-4783-bff1-27960b90b96c/screenshot_dashboard_encore.png')

        await browser.close()

if __name__ == '__main__':
    asyncio.run(run())
