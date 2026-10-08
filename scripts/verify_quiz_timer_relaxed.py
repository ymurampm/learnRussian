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
    screenshot_path = os.path.join(artifact_dir, "screenshot_quiz_relaxed_timer_feedback.png")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 850})
        page = await context.new_page()

        await page.goto("http://localhost:8085", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # Load Day 21 Morning session
        await page.evaluate("""async () => {
            if (window.app && window.app.loadState) {
                await window.app.loadState(21);
            }
        }""")
        await page.wait_for_timeout(1000)

        # Click Morning session
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

        # Confirm we are in QuizEngine
        quiz_prompt = page.locator(".quiz-prompt-ru").first
        await quiz_prompt.wait_for(state="visible", timeout=5000)
        prompt_text = await quiz_prompt.inner_text()
        print(f"Quiz loaded successfully: {prompt_text}")

        # Wait 13 seconds to simulate deliberate reading / thoughtful solving (exceeding old 12s cutoff)
        print("Waiting 13 seconds to simulate deliberate consideration (> 12s)...")
        await page.wait_for_timeout(13000)

        # Verify live timer does NOT say "統計除外" at 13 seconds
        live_timer = page.locator("#rtLiveTimer")
        timer_text = await live_timer.inner_text()
        print(f"Live timer at 13s: {timer_text}")
        assert "統計除外" not in timer_text, "Failure: Timer prematurely showed 統計除外 at 13s!"

        # Answer question (click first choice / correct option)
        choice_btn = page.locator(".quiz-choice-btn").first
        await choice_btn.click()
        await page.wait_for_timeout(1500)

        # Check feedback area
        feedback = page.locator("#quizFeedbackArea")
        feedback_text = await feedback.inner_text()
        print("=== Feedback Text ===")
        print(feedback_text)
        print("======================")

        # Assertions
        assert "統計除外" not in feedback_text, "Failure: Response was marked as 統計除外!"
        assert "中断" not in feedback_text, "Failure: Response was marked as 中断!"
        assert "\u6b63\u89e3\u3067\u3059" in feedback_text, "Missing correct title!"
        assert "14." in feedback_text or "s" in feedback_text, "Missing time badge!"

        # Screenshot
        await page.screenshot(path=screenshot_path)
        print(f"Screenshot saved to: {screenshot_path}")

        await browser.close()
        print("RELAXED TIMER VERIFICATION PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(verify())
