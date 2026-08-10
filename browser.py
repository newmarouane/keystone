import os

from patchright.async_api import BrowserContext, Page, async_playwright


CHROME_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-blink-features=AutomationControlled",
    "--no-first-run",
    "--no-default-browser-check",
]

USER_DATA_DIR = os.getenv("BROWSER_PROFILE", "/app/profile")


async def start_browser():
    playwright = await async_playwright().start()

    context = await playwright.chromium.launch_persistent_context(
        user_data_dir=USER_DATA_DIR,
        headless=True,
        locale="en-US",
        permissions=[
            "clipboard-read",
            "clipboard-write",
        ],
        args=CHROME_ARGS,
    )

    page = (
        context.pages[0]
        if context.pages
        else await context.new_page()
    )

    return playwright, context, page


async def create_new_page(context: BrowserContext) -> Page:
    return await context.new_page()
