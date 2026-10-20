import asyncio
import sys
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding='utf-8')

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1280, 'height': 900})
        await page.goto('http://localhost:8085')
        await page.wait_for_timeout(2000)

        print("Loading Day 38 and starting morning lesson...")
        await page.evaluate('''async () => {
            await window.App.loadState(38);
            const morning = window.App.state.today_pack.sessions.morning;
            window.App.startLesson(morning, 'morning');
            window.LessonPlayer.setPhase(2);
        }''')
        await page.wait_for_timeout(1500)

        # Find the token with text "пошла" and click it
        print("Looking for 'пошла' token in Phase 2...")
        token_found = await page.evaluate('''() => {
            const tokens = Array.from(document.querySelectorAll('.token-item, .token, [data-word]'));
            const target = tokens.find(el => el.innerText.includes('пошла') || el.dataset.word === 'пошла');
            if (target) {
                target.click();
                return true;
            }
            return false;
        }''')
        print("Token clicked:", token_found)

        if not token_found:
            # Direct trigger via BranchExplorer API
            print("Triggering BranchExplorer directly...")
            await page.evaluate('''() => {
                if (window.BranchExplorer) {
                    window.BranchExplorer.selectWord('пошла', {
                        word: 'пошла',
                        base: 'пойти',
                        tag: 'syntax.conditional',
                        role: '動詞（行くだろうに / 過去女性）',
                        grammar: '過去・女性単数'
                    });
                }
            }''')

        await page.wait_for_timeout(1500)

        # Inspect table and headers
        modal_info = await page.evaluate('''() => {
            const container = document.getElementById('branchExplorerContainer') || document.querySelector('.branch-explorer-pane') || document.body;
            const text = container.innerText;
            const table = container.querySelector('table');
            const rows = table ? Array.from(table.querySelectorAll('tr')).map(tr => Array.from(tr.querySelectorAll('th, td')).map(td => td.innerText.trim())) : [];
            const banner = container.querySelector('.irregular-alert-banner')?.innerText || '';
            const toolbar = container.querySelector('.conjugation-recite-toolbar')?.innerText || '';
            return {
                banner,
                toolbar,
                rows,
                hasPoydu: text.includes('пойду'),
                hasPoydesh: text.includes('пойдёшь'),
                hasBogusPoyish: text.includes('пойишь') || text.includes('пойю')
            };
        }''')

        print("=== MODAL INSPECTION RESULTS ===")
        print("Alert banner:", modal_info.get('banner'))
        print("Recite toolbar:", modal_info.get('toolbar'))
        print("Table rows:")
        for r in modal_info.get('rows', []):
            print("  ", r)
        print("Has genuine forms (пойду, пойдёшь):", modal_info.get('hasPoydu') and modal_info.get('hasPoydesh'))
        print("Has bogus forms (пойю, пойишь):", modal_info.get('hasBogusPoyish'))

        # Take screenshot of the modal
        screenshot_path = 'C:/Users/ymura/.gemini/antigravity/brain/bbc31de0-69a0-4783-bff1-27960b90b96c/day38_poshla_fixed.png'
        await page.screenshot(path=screenshot_path)
        print(f"Screenshot saved to: {screenshot_path}")

        await browser.close()

if __name__ == '__main__':
    asyncio.run(run())
