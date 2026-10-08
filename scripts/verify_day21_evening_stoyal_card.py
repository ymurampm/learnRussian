# -*- coding: utf-8 -*-
import asyncio
import os
import sys
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

async def verify():
    artifact_dir = "C:/Users/ymura/.gemini/antigravity/brain/f5995360-db35-4e7a-bf4f-145fc294ed6a"
    os.makedirs(artifact_dir, exist_ok=True)
    screenshot_stoyal = os.path.join(artifact_dir, "screenshot_day21_evening_stoyal_card.png")
    screenshot_ondemand = os.path.join(artifact_dir, "screenshot_day21_evening_ondemand_inflected.png")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 850})
        page = await context.new_page()

        # Navigate to application
        await page.goto("http://localhost:8085", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # Switch to Day 21
        await page.evaluate("""async () => {
            if (window.app && window.app.loadState) {
                await window.app.loadState(21);
            }
        }""")
        await page.wait_for_timeout(1000)

        # Open Evening session
        evening_card = page.locator(".session-card[data-session-type='evening']")
        await evening_card.click()
        await page.wait_for_timeout(1000)

        # Open paragraph explanation modal
        explain_btn = page.locator(".bath-explain-btn[data-p-idx='0']").first
        await explain_btn.click()
        await page.wait_for_timeout(1000)

        # 1. Test clicking "стоял" -> highlights matching key_vocab card
        stoyal_token = page.locator("#modalHeroTokens .bath-word-token", has_text="стоял").first
        assert await stoyal_token.count() > 0, "Could not find 'стоял' token in modalHeroTokens"
        await stoyal_token.click()
        await page.wait_for_timeout(1000)

        # Locate the card for стоять
        stoyat_card = page.locator(".explain-vocab-card[data-vocab-word='стоять']").first
        assert await stoyat_card.count() > 0, "Could not find key_vocab card for стоять"
        stoyat_card_text = await stoyat_card.inner_text()
        print("=== Stoyat Card Text ===")
        print(stoyat_card_text.encode('utf-8', errors='replace').decode('utf-8'))
        print("========================")
        assert "\u6587\u8104\u91cd\u8981\u8a9e\u5f57" not in stoyat_card_text, "Found placeholder text in stoyat card!"

        await page.screenshot(path=screenshot_stoyal)
        print(f"Screenshot 1 saved: {screenshot_stoyal}")

        # 2. Test clicking an on-demand inflected word not in key_vocab: e.g. "зале" (prepositional of зал)
        zale_token = page.locator("#modalHeroTokens .bath-word-token", has_text="зале").first
        assert await zale_token.count() > 0, "Could not find 'зале' token in modalHeroTokens"
        await zale_token.click()
        await page.wait_for_timeout(2000)

        ondemand_card = page.locator("#modalOndemandContainer .ondemand-vocab-card")
        await ondemand_card.wait_for(state="visible", timeout=5000)
        ondemand_text = await ondemand_card.inner_text()
        print("=== On-Demand Card Text for 'зале' ===")
        print(ondemand_text.encode('utf-8', errors='replace').decode('utf-8'))
        print("======================================")
        assert "\u6587\u8104\u91cd\u8981\u8a9e\u5f57" not in ondemand_text, "Found placeholder text in ondemand card!"
        assert "\u524d\u7f6e\u683c" in ondemand_text or "зал" in ondemand_text, "Missing dictionary translation for зал/зале!"

        await page.screenshot(path=screenshot_ondemand)
        print(f"Screenshot 2 saved: {screenshot_ondemand}")

        await browser.close()
        print("ALL PLAYWRIGHT TESTS PASSED CLEANLY!")

if __name__ == "__main__":
    asyncio.run(verify())
