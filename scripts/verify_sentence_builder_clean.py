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
    screenshot_path = os.path.join(artifact_dir, "screenshot_sentence_builder_no_punctuation.png")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 850})
        page = await context.new_page()

        await page.goto("http://localhost:8085", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # Click Morning session card on dashboard
        morning_card = page.locator(".session-card[data-session-type='morning']")
        await morning_card.click()
        await page.wait_for_timeout(1000)

        # Jump directly to Phase 3 (確かめる)
        await page.evaluate("""() => {
            if (window.LessonPlayer) {
                window.LessonPlayer.setPhase(3);
            }
        }""")
        await page.wait_for_timeout(1000)

        # Wait for quiz container
        await page.locator(".quiz-container").wait_for(state="visible", timeout=5000)

        # Answer Q1
        q1_btn = page.locator(".quiz-choice-btn").first
        await q1_btn.click()
        await page.wait_for_timeout(400)
        await page.locator("#quizNextBtn").click()
        await page.wait_for_timeout(600)

        # Answer Q2
        q2_btn = page.locator(".quiz-choice-btn").first
        await q2_btn.click()
        await page.wait_for_timeout(400)
        await page.locator("#quizNextBtn").click()
        await page.wait_for_timeout(600)

        # Now on Q3: Sentence Builder
        bank = page.locator("#builderBank")
        await bank.wait_for(state="visible", timeout=5000)

        token_badges = page.locator(".builder-token-badge")
        count = await token_badges.count()
        print(f"Total token badges found on Question 3: {count}")
        badge_texts = []
        for i in range(count):
            t = await token_badges.nth(i).locator("span").inner_text()
            badge_texts.append(t)
            print(f"Token {i+1}: '{t}'")
            assert not t.endswith('.'), f"Error: Token '{t}' ends with a period!"
            assert not t.endswith(','), f"Error: Token '{t}' ends with a comma!"
            assert not t.endswith('!'), f"Error: Token '{t}' ends with an exclamation!"
            assert not t.endswith('?'), f"Error: Token '{t}' ends with a question mark!"

        print("SUCCESS! All sentence builder tokens are 100% free of punctuation clues!")

        # Take screenshot of the cleaned sentence builder UI
        await page.screenshot(path=screenshot_path)
        print(f"Cleaned UI screenshot saved to: {screenshot_path}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(verify())
