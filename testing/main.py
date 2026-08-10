import asyncio
from patchright.async_api import async_playwright

async def launch_browser():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(locale="en-US",permissions=["clipboard-read", "clipboard-write"])
        page = await context.new_page()
        await page.goto(
            "https://chatgpt.com/",
            wait_until="networkidle"
        )
        editor = page.locator("#prompt-textarea")
        print("Waiting for the editor to become visible...")
        await editor.wait_for(state="visible")
        print("Editor is visible!")
        await editor.click()
        await editor.press_sequentially("give me all the info that u know about Youssef Ghafir")
        await editor.press("Enter")

        stop_button = page.get_by_role("button", name="Copy response")
        await stop_button.wait_for(state="visible")
        print("Generation finished")
        await stop_button.click()
        text = await page.evaluate("""
async () => {
    return await navigator.clipboard.readText();
}
""")
        print(text)
        await page.wait_for_timeout(10000)  # Wait for 5 seconds to observe the result
        await browser.close()

asyncio.run(launch_browser())