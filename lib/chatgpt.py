import asyncio
import json
import time
from pathlib import Path

from patchright.async_api import (
    Page,
    TimeoutError as PlaywrightTimeoutError,
)


# ============================================================
# CONFIGURATION
# ============================================================

CHATGPT_URL = "https://chatgpt.com/"

PAGE_LOAD_TIMEOUT = 600_000
NETWORK_IDLE_TIMEOUT = 200_000
EDITOR_TIMEOUT = 600_000

GENERATION_TIMEOUT = 3000

DEBUG_DIR = Path("/app/debug")
DEBUG_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# DEBUG HELPERS
# ============================================================

async def save_debug_info(
    page: Page,
    prefix: str = "chatgpt",
):
    """
    Save debugging information safely even if the page is
    navigating/reloading because of a Cloudflare challenge.
    """

    timestamp = int(time.time())

    screenshot_path = DEBUG_DIR / (
        f"{prefix}-{timestamp}.png"
    )

    html_path = DEBUG_DIR / (
        f"{prefix}-{timestamp}.html"
    )

    text_path = DEBUG_DIR / (
        f"{prefix}-{timestamp}.txt"
    )

    # ========================================================
    # Current URL
    # ========================================================

    try:
        current_url = page.url
    except Exception:
        current_url = ""

    print(
        f"[DEBUG] URL: {current_url}"
    )

    # ========================================================
    # Screenshot
    # ========================================================

    try:

        await page.screenshot(
            path=str(screenshot_path),
            full_page=True,
            timeout=10000,
        )

        print(
            f"[DEBUG] Screenshot saved: "
            f"{screenshot_path}"
        )

    except Exception as e:

        print(
            f"[DEBUG] Could not save screenshot: {e}"
        )

    # ========================================================
    # HTML
    # ========================================================

    try:

        html = await page.content()

        html_path.write_text(
            html,
            encoding="utf-8",
        )

        print(
            f"[DEBUG] HTML saved: "
            f"{html_path}"
        )

    except Exception as e:

        print(
            f"[DEBUG] Could not save HTML: {e}"
        )

    # ========================================================
    # BODY TEXT
    # ========================================================

    try:

        body_text = await page.locator(
            "body"
        ).inner_text(
            timeout=5000
        )
        print(body_text)
        text_path.write_text(
            body_text,
            encoding="utf-8",
        )

        print(
            f"[DEBUG] Body text saved: "
            f"{text_path}"
        )

        print(
            "[DEBUG] Body preview:"
        )

        print(
            body_text[:3000]
        )

    except Exception as e:

        print(
            f"[DEBUG] Could not save body text: {e}"
        )

    # ========================================================
    # BROWSER INFORMATION
    # ========================================================

    try:

        browser_info = await page.evaluate(
            """
            () => ({
                userAgent: navigator.userAgent,
                platform: navigator.platform,
                language: navigator.language,
                languages: navigator.languages,
                webdriver: navigator.webdriver,
                readyState: document.readyState,
                width: window.innerWidth,
                height: window.innerHeight,
                devicePixelRatio: window.devicePixelRatio
            })
            """
        )

        print(
            "[DEBUG] Browser information:"
        )

        print(
            json.dumps(
                browser_info,
                indent=2,
                ensure_ascii=False,
            )
        )

    except Exception as e:

        # This is expected if Cloudflare has just
        # navigated/reloaded the page.

        print(
            "[DEBUG] Could not get browser information: "
            f"{e}"
        )

    # ========================================================
    # PAGE TITLE
    # ========================================================

    try:

        title = await page.title()

        print(
            f"[DEBUG] Page title: {title!r}"
        )

    except Exception as e:

        print(
            f"[DEBUG] Could not get page title: {e}"
        )

    print(
        "[DEBUG] Diagnostics completed."
    )


# ============================================================
# PAGE INFORMATION
# ============================================================

async def get_page_title(
    page: Page,
) -> str:

    try:

        return await page.title()

    except Exception:

        return ""


async def get_body_html(
    page: Page,
) -> str:

    try:

        return await page.content()

    except Exception:

        return ""


# ============================================================
# CLOUDFLARE DETECTION
# ============================================================

async def detect_cloudflare_challenge(
    page: Page,
) -> bool:
    """
    Detect Cloudflare managed challenges.

    This checks the actual HTML markers observed in the
    current ChatGPT Cloudflare challenge page.

    It DOES NOT attempt to bypass the challenge.
    """

    try:

        url = page.url.lower()

    except Exception:

        url = ""

    title = (
        await get_page_title(page)
    ).lower()

    html = (
        await get_body_html(page)
    ).lower()

    # --------------------------------------------------------
    # URL indicators
    # --------------------------------------------------------

    url_indicators = [
        "__cf_chl_rt_tk",
        "__cf_chl_tk",
        "__cf_chl_f_tk",
        "/cdn-cgi/challenge-platform/",
    ]

    # --------------------------------------------------------
    # Title indicators
    # --------------------------------------------------------

    title_indicators = [
        "just a moment",
        "checking your browser",
        "verify you are human",
    ]

    # --------------------------------------------------------
    # Actual Turnstile / challenge markers
    # --------------------------------------------------------

    html_indicators = [
        "cf-turnstile-response",
        "challenges.cloudflare.com/turnstile",
        "/cdn-cgi/challenge-platform/",
        "challenge-platform",
        "verification successful",
        "enable javascript and cookies to continue",
    ]

    url_match = any(
        x in url
        for x in url_indicators
    )

    title_match = any(
        x in title
        for x in title_indicators
    )

    html_matches = [
        x
        for x in html_indicators
        if x in html
    ]

    # --------------------------------------------------------
    # Strong detection
    # --------------------------------------------------------

    if (
        title_match
        and len(html_matches) >= 2
    ):
        return True

    if (
        url_match
        and (
            title_match
            or len(html_matches) >= 2
        )
    ):
        return True

    return False


# ============================================================
# WAIT FOR CHATGPT OR CHALLENGE
# ============================================================

async def wait_for_chatgpt(
    page: Page,
):
    """
    Wait until either:

    1. ChatGPT editor appears
    2. Cloudflare challenge is detected
    3. Timeout occurs
    """

    start = (
        asyncio.get_running_loop().time()
    )

    timeout_seconds = (
        EDITOR_TIMEOUT / 1000
    )

    while True:

        # ----------------------------------------------------
        # Cloudflare
        # ----------------------------------------------------

        if await detect_cloudflare_challenge(
            page
        ):

            await save_debug_info(
                page,
                prefix="cloudflare",
            )

            raise RuntimeError(
                "Cloudflare managed security "
                "challenge detected on chatgpt.com."
            )

        # ----------------------------------------------------
        # Try editor
        # ----------------------------------------------------

        selectors = [
            "#prompt-textarea",
            "textarea[placeholder*='Message']",
            "textarea",
            "[contenteditable='true']",
        ]

        for selector in selectors:

            try:

                locator = page.locator(
                    selector
                ).last

                if await locator.is_visible(
                    timeout=10000
                ):

                    print(
                        "[CHATGPT] Editor found using: "
                        f"{selector}"
                    )

                    return locator

            except Exception:

                pass

        # ----------------------------------------------------
        # Timeout
        # ----------------------------------------------------

        elapsed = (
            asyncio.get_running_loop().time()
            - start
        )

        if elapsed >= timeout_seconds:

            await save_debug_info(
                page,
                prefix="editor-timeout",
            )

            raise RuntimeError(
                "ChatGPT editor was not found "
                f"within {EDITOR_TIMEOUT / 1000:.0f} seconds."
            )

        await asyncio.sleep(
            0.5
        )


# ============================================================
# BROWSER INFORMATION
# ============================================================

async def print_browser_information(
    page: Page,
):

    try:

        information = await page.evaluate(
            """
            () => ({
                userAgent: navigator.userAgent,
                platform: navigator.platform,
                language: navigator.language,
                languages: navigator.languages,
                webdriver: navigator.webdriver,
                readyState: document.readyState,
                width: window.innerWidth,
                height: window.innerHeight,
                devicePixelRatio: window.devicePixelRatio
            })
            """
        )

        print(
            "[BROWSER] Information:"
        )

        print(
            json.dumps(
                information,
                indent=2,
                ensure_ascii=False,
            )
        )

        return information

    except Exception as e:

        print(
            "[BROWSER] Could not get browser information: "
            f"{type(e).__name__}: {e}"
        )

        return None


# ============================================================
# COOKIE INFORMATION
# ============================================================

async def print_cookie_information(
    page: Page,
):

    try:

        cookies = await page.context.cookies()

        print(
            f"[AUTH] Total cookies: {len(cookies)}"
        )

        for cookie in cookies:

            domain = cookie.get(
                "domain",
                "",
            )

            name = cookie.get(
                "name",
                "",
            )

            if (
                "chatgpt" in domain.lower()
                or "openai" in domain.lower()
            ):

                print(
                    "[AUTH] Cookie:"
                    f" {name} @ {domain}"
                )

    except Exception as e:

        print(
            f"[AUTH] Cookie inspection error: {e}"
        )


# ============================================================
# ENSURE CHATGPT PAGE
# ============================================================

async def ensure_chatgpt_page(page: Page):

    print("[CHATGPT] Loading ChatGPT...")

    if not page.url.startswith("https://chatgpt.com"):
        print(
            f"[CHATGPT] Navigating to: {CHATGPT_URL}"
        )

        await page.goto(
            CHATGPT_URL,
            wait_until="domcontentloaded",
            timeout=60000,
        )

    # Allow Cloudflare / frontend navigation to settle.
    await asyncio.sleep(3)

    print(
        f"[CHATGPT] URL: {page.url}"
    )

    title = ""

    try:
        title = await page.title()
    except Exception:
        pass

    print(
        f"[CHATGPT] Title: {title!r}"
    )

    # --------------------------------------------------------
    # IMPORTANT: check Cloudflare BEFORE browser evaluate
    # --------------------------------------------------------

    if await detect_cloudflare_challenge(page):

        print(
            "[SECURITY] Cloudflare challenge detected."
        )

        await save_debug_info(
            page,
            prefix="cloudflare",
        )

        raise RuntimeError(
            "Cloudflare/security challenge detected.\n"
            f"URL: {page.url}\n"
            f"Title: {title!r}"
        )

    # --------------------------------------------------------
    # Now the actual ChatGPT application should exist
    # --------------------------------------------------------

    editor = await wait_for_chatgpt(page)

    print(
        "[CHATGPT] ChatGPT interface loaded."
    )

    return editor


# ============================================================
# SUBMIT PROMPT
# ============================================================

async def submit_prompt(
    page: Page,
    editor,
    prompt: str,
):

    print(
        "[CHATGPT] Submitting prompt..."
    )

    await editor.click()

    # --------------------------------------------------------
    # Try fill first
    # --------------------------------------------------------

    try:

        await editor.fill(
            prompt
        )

        print(
            "[CHATGPT] Prompt filled."
        )

    except Exception as e:

        print(
            "[CHATGPT] fill() failed:"
            f" {e}"
        )

        print(
            "[CHATGPT] Falling back to typing."
        )

        await editor.press_sequentially(
            prompt,
            delay=1,
        )

    await asyncio.sleep(
        0.2
    )

    await editor.press(
        "Enter"
    )

    print(
        "[CHATGPT] Prompt submitted."
    )


# ============================================================
# FIND LAST ASSISTANT MESSAGE
# ============================================================

async def get_last_assistant_message(
    page: Page,
):

    selectors = [
        '[data-message-author-role="assistant"]',
        '[data-message-author-role="assistant"] .markdown',
    ]

    for selector in selectors:

        try:

            locator = page.locator(
                selector
            )

            count = await locator.count()

            if count == 0:
                continue

            last = locator.last

            return last

        except Exception:

            continue

    return None


# ============================================================
# GET MESSAGE TEXT
# ============================================================

async def get_assistant_text(
    assistant_message,
):

    if assistant_message is None:

        return ""

    try:

        return (
            await assistant_message.inner_text(
                timeout=50000
            )
            or ""
        )

    except Exception:

        return ""


# ============================================================
# DETECT GENERATION
# ============================================================

async def is_chatgpt_generating(
    page: Page,
):

    selectors = [
        'button[aria-label="Stop answer"]',
        'button[aria-label="Stop generating"]',
        'button[title="Stop generating"]',
        'button:has-text("Stop generating")',
        'button:has-text("Stop answer")',
    ]

    for selector in selectors:

        try:

            locator = page.locator(
                selector
            ).last

            if await locator.is_visible(
                timeout=5000
            ):

                return True

        except Exception:

            pass

    return False


# ============================================================
# WAIT FOR RESPONSE
# ============================================================

async def wait_for_response(
    page: Page,
):

    start = (
        asyncio.get_running_loop().time()
    )

    last_text = ""

    started = False

    stable_count = 0

    while True:

        elapsed = (
            asyncio.get_running_loop().time()
            - start
        )

        if elapsed > GENERATION_TIMEOUT:

            raise RuntimeError(
                "ChatGPT response generation "
                "timed out."
            )

        await asyncio.sleep(
            0.3
        )

        assistant = (
            await get_last_assistant_message(
                page
            )
        )

        if assistant is None:

            continue

        text = (
            await get_assistant_text(
                assistant
            )
        )

        if not text:

            continue

        if text != last_text:

            last_text = text

            started = True

            stable_count = 0

            continue

        if not started:

            continue

        generating = (
            await is_chatgpt_generating(
                page
            )
        )

        if generating:

            stable_count = 0

            continue

        stable_count += 1

        # Require the response to remain stable
        # for several polling cycles.

        if stable_count >= 4:

            return last_text


# ============================================================
# NON-STREAMING
# ============================================================

async def chatgpt_handle_response(
    page: Page,
    context,
    question: str,
) -> str:

    try:
        editor = await ensure_chatgpt_page(page)

        await submit_prompt(
            page,
            editor,
            question,
        )

        print(
            "[CHATGPT] Waiting for response..."
        )

        response = await wait_for_response(page)

        print(
            "[CHATGPT] Generation finished."
        )

        return response

    except Exception as e:
        print(e)
        print(
            "[CHATGPT] Error while processing request:"
        )

        print(
            f"{type(e).__name__}: {e}"
        )

        # IMPORTANT:
        # Do NOT call save_debug_info() here.
        #
        # ensure_chatgpt_page() already saves diagnostics
        # when a Cloudflare challenge is detected.

        return (
            e
        )

# ============================================================
# STREAMING
# ============================================================

async def stream_chatgpt_response(
    page: Page,
    prompt: str,
    newContext: bool,
):

    try:

        editor = await ensure_chatgpt_page(
            page
        )

        await submit_prompt(
            page,
            editor,
            prompt,
        )

        await asyncio.sleep(
            0.5
        )

        last_text = ""

        started = False

        start_time = (
            asyncio.get_running_loop().time()
        )

        stable_count = 0

        while True:

            # ------------------------------------------------
            # Timeout
            # ------------------------------------------------

            elapsed = (
                asyncio.get_running_loop().time()
                - start_time
            )

            if elapsed > GENERATION_TIMEOUT:

                await save_debug_info(
                    page,
                    prefix="generation-timeout",
                )

                raise RuntimeError(
                    "ChatGPT generation timed out."
                )

            await asyncio.sleep(
                0.2
            )

            # ------------------------------------------------
            # Find assistant message
            # ------------------------------------------------

            assistant = (
                await get_last_assistant_message(
                    page
                )
            )

            if assistant is None:

                continue

            # ------------------------------------------------
            # Read current text
            # ------------------------------------------------

            current_text = (
                await get_assistant_text(
                    assistant
                )
            )

            if not current_text:

                continue

            # ------------------------------------------------
            # New content
            # ------------------------------------------------

            if current_text != last_text:

                started = True

                stable_count = 0

                payload = json.dumps(
                    {
                        "text": current_text
                    },
                    ensure_ascii=False,
                )

                yield (
                    f"data: {payload}\n\n"
                )

                last_text = current_text

                continue

            # ------------------------------------------------
            # Don't finish before response starts
            # ------------------------------------------------

            if not started:

                continue

            # ------------------------------------------------
            # Check generation
            # ------------------------------------------------

            generating = (
                await is_chatgpt_generating(
                    page
                )
            )

            if generating:

                stable_count = 0

                continue

            # ------------------------------------------------
            # Require stability
            # ------------------------------------------------

            stable_count += 1

            if stable_count < 4:

                continue

            # ------------------------------------------------
            # Final read
            # ------------------------------------------------

            assistant = (
                await get_last_assistant_message(
                    page
                )
            )

            final_text = (
                await get_assistant_text(
                    assistant
                )
            )

            if final_text != last_text:

                payload = json.dumps(
                    {
                        "text": final_text
                    },
                    ensure_ascii=False,
                )

                yield (
                    f"data: {payload}\n\n"
                )

                last_text = final_text

                stable_count = 0

                continue

            # ------------------------------------------------
            # Finished
            # ------------------------------------------------

            print(
                "[CHATGPT] Generation finished."
            )

            yield (
                "data: [DONE]\n\n"
            )

            # ------------------------------------------------
            # Close page if requested
            # ------------------------------------------------

            if newContext:

                try:

                    await page.close()

                except Exception as e:

                    print(
                        "[CHATGPT] "
                        f"Page close error: {e}"
                    )

            break

    except Exception as e:

        print()
        print(
            "[CHATGPT] Streaming error:"
        )

        print(
            f"{type(e).__name__}: {e}"
        )

        try:

            await save_debug_info(
                page,
                prefix="stream-error",
            )

        except Exception:
            pass

        payload = json.dumps(
            {
                "error": (
                    "An error occurred while "
                    "processing the ChatGPT request."
                ),
                "type": type(e).__name__,
                "message": str(e),
            },
            ensure_ascii=False,
        )

        yield (
            f"data: {payload}\n\n"
        )

        yield (
            "data: [DONE]\n\n"
        )


# ============================================================
# TEST FUNCTION
# ============================================================

async def test_chatgpt(
    page: Page,
):

    print()
    print(
        "=" * 70
    )
    print(
        "CHATGPT TEST"
    )
    print(
        "=" * 70
    )

    try:

        editor = await ensure_chatgpt_page(
            page
        )

        print(
            "[TEST] ChatGPT interface detected."
        )

        try:

            tag = await editor.evaluate(
                "el => el.tagName"
            )

            element_id = await editor.get_attribute(
                "id"
            )

            print(
                f"[TEST] Tag: {tag}"
            )

            print(
                f"[TEST] ID: {element_id}"
            )

        except Exception:
            pass

        return True

    except Exception as e:

        print(
            "[TEST] FAILED:"
        )

        print(
            f"{type(e).__name__}: {e}"
        )

        return False
