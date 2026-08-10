from patchright.async_api import Browser, async_playwright
import random
chrome_args = [
        "--disable-blink-features=AutomationControlled",  # hide navigator.webdriver
        "--no-first-run",
        "--no-default-browser-check",
]
VIEWPORT_WIDTH = 1280
VIEWPORT_HEIGHT = 800
async def start_browser() -> tuple[Browser, async_playwright]:
    launch_kwargs = dict(
        args=chrome_args,
        locale="en-US",permissions=["clipboard-read", "clipboard-write"]
    )
    playwright = await async_playwright().start()
    context = await playwright.chromium.launch_persistent_context(headless=False, 
                                                   user_data_dir="./profile",
                                               **launch_kwargs)
    page = context.pages[0] if context.pages else await context.new_page()
    
    return playwright, context, page

async def create_new_page(context: Browser):
    page = await context.new_page()
    return page



# This appraoch without presistent context
# async def create_new_context(browser: Browser):
#     width = VIEWPORT_WIDTH + random.randint(-20, 20)
#     height = VIEWPORT_HEIGHT + random.randint(-20, 20)
#     context = await browser.new_context(viewport={"width": width, "height": height},locale="en-US",permissions=["clipboard-read", "clipboard-write"])
#     return context
# async def create_page(browser: Browser):
#     context = await create_new_context(browser)
#     page = await context.new_page()
#     return context, page

# ====================================================
# async def start_browser() -> tuple[Browser, async_playwright]:
#     launch_kwargs = dict(
#         args=chrome_args,
#     )
#     playwright = await async_playwright().start()
#     browser = await playwright.chromium.launch_persistent_context(headless=False, 
#                                                    user_data_dir="./profile",
#                                                **launch_kwargs)
    
#     return browser, playwright