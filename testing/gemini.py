import asyncio
from patchright.async_api import async_playwright

async def launch_browser():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(locale="en-US")
        page = await context.new_page()

        await page.goto(
            "https://gemini.google.com/app",
            wait_until="networkidle"
        )

        editor = page.locator(".ql-editor")
        print("Waiting for the editor to become visible...")
        await editor.wait_for(state="visible")
        print("Editor is visible!")
        await editor.click()
        await editor.press_sequentially("let's write a story about a brave knight who saves a village from a dragon.")
        await editor.press("Enter")

        stop_button = page.get_by_role("button", name="Stop response")
        result = await stop_button.wait_for(state="visible")
        print("stop is here ", result)
        print("Generation started")
        await stop_button.wait_for(state="hidden")
        print("Generation finished")
        element = page.locator("structured-content-container")
        content = await element.text_content()
        print("Generated content:", content)
        await page.wait_for_timeout(10000)  # Wait for 5 seconds to observe the result
        await browser.close()

asyncio.run(launch_browser())