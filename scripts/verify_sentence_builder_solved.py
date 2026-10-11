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
    screenshot_path = os.path.join(artifact_dir, "screenshot_sentence_builder_solved_clean.png")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 850})
        page = await context.new_page()

        await page.goto("http://localhost:8085", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # Click Morning session card
        morning_card = page.locator(".session-card[data-session-type='morning']")
        await morning_card.click()
        await page.wait_for_timeout(1000)

        # Jump to Phase 3
        await page.evaluate("""() => {
            if (window.LessonPlayer) {
                window.LessonPlayer.setPhase(3);
            }
        }""")
        await page.wait_for_timeout(1000)

        # Skip Q1 & Q2
        q1_btn = page.locator(".quiz-choice-btn").first
        await q1_btn.click()
        await page.wait_for_timeout(300)
        await page.locator("#quizNextBtn").click()
        await page.wait_for_timeout(500)

        q2_btn = page.locator(".quiz-choice-btn").first
        await q2_btn.click()
        await page.wait_for_timeout(300)
        await page.locator("#quizNextBtn").click()
        await page.wait_for_timeout(500)

        # Solve Q3: "В библиотеке не хватало пяти экземпляров партитуры"
        target_words = ["В", "библиотеке", "не", "хватало", "пяти", "экземпляров", "партитуры"]
        for word in target_words:
            btn = page.locator(f"#builderBank .builder-token-badge[data-token='{word}']")
            await btn.click()
            await page.wait_for_timeout(150)

        await page.wait_for_timeout(800)

        # Check feedback area has correct feedback
        feedback_el = page.locator("#quizFeedbackArea")
        feedback_text = await feedback_el.inner_text()
        print(f"Feedback displayed: {feedback_text[:100]}...")
        assert "正解" in feedback_text or "В библиотеке не хватало пяти экземпляров партитуры" in feedback_text, "Feedback did not show expected result!"

        # Take screenshot of solved screen
        await page.screenshot(path=screenshot_path)
        print(f"Solved UI screenshot saved to: {screenshot_path}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(verify())
