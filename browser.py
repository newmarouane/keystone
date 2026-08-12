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

    browser = await playwright.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
        ],
    )

    context = await browser.new_context(
        viewport={
            "width": 1280,
            "height": 800,
        },
    )

    page = await context.new_page()

    return playwright, browser, context, page


async def create_new_page(context: BrowserContext) -> Page:
    return await context.new_page()
