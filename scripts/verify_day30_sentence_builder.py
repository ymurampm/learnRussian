# -*- coding: utf-8 -*-
import asyncio
import os
import sys
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

async def verify_day30():
    artifact_dir = "C:/Users/ymura/.gemini/antigravity/brain/f5995360-db35-4e7a-bf4f-145fc294ed6a"
    os.makedirs(artifact_dir, exist_ok=True)
    screenshot_path = os.path.join(artifact_dir, "screenshot_day30_sentence_builder_clean.png")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 850})
        page = await context.new_page()

        await page.goto("http://localhost:8085", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # Click Morning session card on dashboard (currently Day 30)
        morning_card = page.locator(".session-card[data-session-type='morning']")
        await morning_card.click()
        await page.wait_for_timeout(1000)

        # Jump directly to Phase 3
        await page.evaluate("""() => {
            if (window.LessonPlayer) {
                window.LessonPlayer.setPhase(3);
            }
        }""")
        await page.wait_for_timeout(1000)

        # Question 1: fill_in_blank -> click first choice & next
        q1_btn = page.locator(".quiz-choice-btn").first
        await q1_btn.click()
        await page.wait_for_timeout(300)
        await page.locator("#quizNextBtn").click()
        await page.wait_for_timeout(500)

        # Question 2: grammaticality -> click True & next
        q2_btn = page.locator("#btnTrue")
        await q2_btn.click()
        await page.wait_for_timeout(300)
        await page.locator("#quizNextBtn").click()
        await page.wait_for_timeout(800)

        # Question 3: sentence_builder for Day 30 morning!
        bank = page.locator("#builderBank")
        await bank.wait_for(state="visible", timeout=5000)

        token_badges = page.locator(".builder-token-badge")
        count = await token_badges.count()
        print(f"Total tokens found for Day 30 Q3: {count}")

        badge_texts = []
        for i in range(count):
            t = await token_badges.nth(i).locator("span").inner_text()
            badge_texts.append(t)
            print(f"  Token {i+1}: '{t}'")
            assert not t.endswith('.'), f"FATAL: Token '{t}' ends with a period!"
            assert not t.endswith(','), f"FATAL: Token '{t}' ends with a comma!"

        assert 'экзамены' in badge_texts, "Token 'экзамены' must be present!"
        assert 'экзамены.' not in badge_texts, "Token 'экзамены.' with period must NOT exist!"

        print("VERIFICATION 100% PASSED: Day 30 sentence builder has ZERO punctuation clues!")

        # Take screenshot of Day 30 Q3 bank
        await page.screenshot(path=screenshot_path)
        print(f"Screenshot saved to: {screenshot_path}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(verify_day30())
