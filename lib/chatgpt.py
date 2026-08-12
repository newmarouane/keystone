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

EDITOR_TIMEOUT = 60_000
PAGE_LOAD_TIMEOUT = 60_000
NETWORK_IDLE_TIMEOUT = 20_000

GENERATION_TIMEOUT = 300  # seconds

DEBUG_DIR = Path("/app/debug")
DEBUG_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# DEBUG
# ============================================================

async def save_debug_info(
    page: Page,
    prefix: str = "chatgpt",
):
    """
    Save screenshot, HTML and body text.

    Files are saved under /app/debug so they can
    optionally be exposed through FastAPI.
    """

    timestamp = int(time.time())

    screenshot_path = (
        DEBUG_DIR
        / f"{prefix}-{timestamp}.png"
    )

    html_path = (
        DEBUG_DIR
        / f"{prefix}-{timestamp}.html"
    )

    body_path = (
        DEBUG_DIR
        / f"{prefix}-{timestamp}.txt"
    )

    # --------------------------------------------------------
    # Screenshot
    # --------------------------------------------------------

    try:

        await page.screenshot(
            path=str(screenshot_path),
            full_page=True,
        )

        print(
            f"[DEBUG] Screenshot saved: "
            f"{screenshot_path}"
        )

    except Exception as e:

        print(
            f"[DEBUG] Screenshot error: {e}"
        )

    # --------------------------------------------------------
    # HTML
    # --------------------------------------------------------

    try:

        html = await page.content()
        print(html)
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
            f"[DEBUG] HTML error: {e}"
        )

    # --------------------------------------------------------
    # Body text
    # --------------------------------------------------------

    try:

        body_text = await page.locator(
            "body"
        ).inner_text(
            timeout=5000
        )

        body_path.write_text(
            body_text,
            encoding="utf-8",
        )

        print(
            f"[DEBUG] Body text saved: "
            f"{body_path}"
        )

        print(
            "[DEBUG] Body preview:"
        )

        print(
            body_text[:3000]
        )

    except Exception as e:

        print(
            f"[DEBUG] Body text error: {e}"
        )

    # --------------------------------------------------------
    # Browser information
    # --------------------------------------------------------

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

        print(
            f"[DEBUG] Browser info error: {e}"
        )


# ============================================================
# PAGE DIAGNOSTICS
# ============================================================

async def print_page_diagnostics(
    page: Page,
):

    print(
        "\n"
        + "=" * 70
    )

    print(
        "CHATGPT PAGE DIAGNOSTICS"
    )

    print(
        "=" * 70
    )

    print(
        f"URL: {page.url}"
    )

    try:

        title = await page.title()

    except Exception:

        title = ""

    print(
        f"TITLE: {title!r}"
    )

    try:

        ready_state = await page.evaluate(
            "() => document.readyState"
        )

        print(
            f"READY STATE: {ready_state}"
        )

    except Exception:
        pass

    try:

        body_text = await page.locator(
            "body"
        ).inner_text(
            timeout=5000
        )

        print(
            "BODY:"
        )

        print(
            body_text[:3000]
        )

    except Exception as e:

        print(
            f"BODY ERROR: {e}"
        )

    print(
        "=" * 70
    )


# ============================================================
# AUTHENTICATION / COOKIES DIAGNOSTICS
# ============================================================

async def inspect_authentication(
    page: Page,
):

    print(
        "[AUTH] Inspecting browser session..."
    )

    try:

        context = page.context

        cookies = await context.cookies()

        print(
            f"[AUTH] Total cookies: "
            f"{len(cookies)}"
        )

        relevant_count = 0

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

                relevant_count += 1

                # IMPORTANT:
                # Never print cookie values.

                print(
                    f"[AUTH] Cookie: "
                    f"{name} @ {domain}"
                )

        print(
            "[AUTH] ChatGPT/OpenAI related "
            f"cookies: {relevant_count}"
        )

    except Exception as e:

        print(
            f"[AUTH] Cookie inspection error: {e}"
        )


# ============================================================
# SECURITY / CLOUDFLARE DETECTION
# ============================================================

async def detect_security_challenge(
    page: Page,
):
    """
    Detect common Cloudflare challenge indicators.

    This function only detects the challenge.
    It does not attempt to bypass it.
    """

    try:

        url = page.url.lower()

    except Exception:

        url = ""

    try:

        title = (
            await page.title()
        ).lower()

    except Exception:

        title = ""

    try:

        html = (
            await page.content()
        ).lower()

    except Exception:

        html = ""

    # --------------------------------------------------------
    # URL indicators
    # --------------------------------------------------------

    url_indicators = [
        "__cf_chl",
        "challenge-platform",
        "cdn-cgi/challenge",
        "cf-chl",
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
    # HTML indicators
    # --------------------------------------------------------

    html_indicators = [
        "just a moment",
        "checking your browser",
        "verify you are human",
        "performing security verification",
        "challenge-platform",
        "cf-chl",
    ]

    url_match = any(
        value in url
        for value in url_indicators
    )

    title_match = any(
        value in title
        for value in title_indicators
    )

    html_match = any(
        value in html
        for value in html_indicators
    )

    if (
        url_match
        or title_match
        or html_match
    ):

        print(
            "[SECURITY] Cloudflare/security "
            "challenge detected."
        )

        print(
            f"[SECURITY] URL: {page.url}"
        )

        print(
            f"[SECURITY] Title: {title!r}"
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


# ============================================================
# BROWSER INFORMATION
# ============================================================

async def print_browser_information(
    page: Page,
):

    try:

        info = await page.evaluate(
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
                info,
                indent=2,
                ensure_ascii=False,
            )
        )

    except Exception as e:

        print(
            f"[BROWSER] Information error: {e}"
        )


# ============================================================
# FIND EDITOR
# ============================================================

async def get_chatgpt_editor(
    page: Page,
):
    """
    Try several possible ChatGPT composer selectors.
    """

    selectors = [
        "#prompt-textarea",
        "textarea[placeholder*='Message']",
        "textarea",
        "[contenteditable='true']",
    ]

    print(
        "[EDITOR] Searching for ChatGPT editor..."
    )

    for selector in selectors:

        try:

            locator = page.locator(
                selector
            ).last

            await locator.wait_for(
                state="visible",
                timeout=5000,
            )

            print(
                "[EDITOR] Found editor using: "
                f"{selector}"
            )

            return locator

        except Exception:

            print(
                "[EDITOR] Not found: "
                f"{selector}"
            )

    raise RuntimeError(
        "Could not find ChatGPT message editor."
    )


# ============================================================
# ENSURE CHATGPT PAGE
# ============================================================

async def ensure_chatgpt_page(
    page: Page,
):

    print(
        "\n"
        + "=" * 70
    )

    print(
        "[CHATGPT] Loading ChatGPT..."
    )

    print(
        "=" * 70
    )

    # --------------------------------------------------------
    # Navigate
    # --------------------------------------------------------

    if not page.url.startswith(
        CHATGPT_URL
    ):

        print(
            f"[CHATGPT] Navigating to: "
            f"{CHATGPT_URL}"
        )

        await page.goto(
            CHATGPT_URL,
            wait_until="domcontentloaded",
            timeout=PAGE_LOAD_TIMEOUT,
        )

    else:

        print(
            "[CHATGPT] Already on ChatGPT."
        )

    print(
        f"[CHATGPT] URL: {page.url}"
    )

    # --------------------------------------------------------
    # Wait for network
    # --------------------------------------------------------

    try:

        await page.wait_for_load_state(
            "networkidle",
            timeout=NETWORK_IDLE_TIMEOUT,
        )

        print(
            "[CHATGPT] Network idle."
        )

    except PlaywrightTimeoutError:

        print(
            "[CHATGPT] Network idle timeout. "
            "Continuing."
        )

    # --------------------------------------------------------
    # Give frontend time to initialize
    # --------------------------------------------------------

    await asyncio.sleep(2)

    # --------------------------------------------------------
    # Basic information
    # --------------------------------------------------------

    try:

        title = await page.title()

    except Exception:

        title = ""

    print(
        f"[CHATGPT] Title: {title!r}"
    )

    print(
        f"[CHATGPT] URL: {page.url}"
    )

    # --------------------------------------------------------
    # Browser information
    # --------------------------------------------------------

    await print_browser_information(
        page
    )

    # --------------------------------------------------------
    # Authentication diagnostics
    # --------------------------------------------------------

    await inspect_authentication(
        page
    )

    # --------------------------------------------------------
    # Cloudflare/security detection
    # --------------------------------------------------------

    await detect_security_challenge(
        page
    )

    # --------------------------------------------------------
    # Find editor
    # --------------------------------------------------------

    try:

        editor = await get_chatgpt_editor(
            page
        )

        print(
            "[CHATGPT] Editor successfully found."
        )

        return editor

    except Exception as e:

        print(
            "[CHATGPT] Editor not found."
        )

        print(
            f"[CHATGPT] Error: {e}"
        )

        await print_page_diagnostics(
            page
        )

        await save_debug_info(
            page,
            prefix="editor-not-found",
        )

        raise RuntimeError(
            "ChatGPT interface did not load.\n"
            f"URL: {page.url}\n"
            f"Title: {title!r}\n"
            f"Original error: {e}"
        ) from e


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
    # Preferred: fill
    # --------------------------------------------------------

    try:

        await editor.fill(
            prompt
        )

    except Exception as fill_error:

        print(
            "[CHATGPT] editor.fill() failed: "
            f"{fill_error}"
        )

        # ----------------------------------------------------
        # Fallback: sequential typing
        # ----------------------------------------------------

        await editor.press_sequentially(
            prompt,
            delay=2,
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
# FIND ASSISTANT MESSAGE
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

            await last.wait_for(
                state="visible",
                timeout=3000,
            )

            return last

        except Exception:

            continue

    return None


# ============================================================
# GET ASSISTANT TEXT
# ============================================================

async def get_assistant_text(
    assistant_message,
):

    if assistant_message is None:

        return ""

    try:

        text = await assistant_message.inner_text(
            timeout=5000
        )

        return text or ""

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
                timeout=1000
            ):

                return True

        except Exception:

            pass

    return False


# ============================================================
# STREAMING RESPONSE
# ============================================================

async def stream_chatgpt_response(
    page: Page,
    prompt: str,
    newContext: bool,
):

    try:

        # ----------------------------------------------------
        # Ensure ChatGPT
        # ----------------------------------------------------

        editor = await ensure_chatgpt_page(
            page
        )

        # ----------------------------------------------------
        # Submit
        # ----------------------------------------------------

        await submit_prompt(
            page,
            editor,
            prompt,
        )

        await asyncio.sleep(
            1
        )

        last_text = ""

        has_started_generating = False

        generation_start = (
            asyncio.get_running_loop().time()
        )

        # ----------------------------------------------------
        # Main loop
        # ----------------------------------------------------

        while True:

            # ------------------------------------------------
            # Timeout
            # ------------------------------------------------

            elapsed = (
                asyncio.get_running_loop().time()
                - generation_start
            )

            if elapsed > GENERATION_TIMEOUT:

                await save_debug_info(
                    page,
                    prefix="generation-timeout",
                )

                raise RuntimeError(
                    "ChatGPT generation timed out "
                    f"after {GENERATION_TIMEOUT} seconds."
                )

            await asyncio.sleep(
                0.2
            )

            # ------------------------------------------------
            # Find assistant message
            # ------------------------------------------------

            assistant_message = (
                await get_last_assistant_message(
                    page
                )
            )

            if assistant_message is None:

                continue

            # ------------------------------------------------
            # Read response
            # ------------------------------------------------

            current_text = (
                await get_assistant_text(
                    assistant_message
                )
            )

            if not current_text:

                continue

            # ------------------------------------------------
            # New text
            # ------------------------------------------------

            if current_text != last_text:

                has_started_generating = True

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
            # Don't finish before generation starts
            # ------------------------------------------------

            if not has_started_generating:

                continue

            # ------------------------------------------------
            # Check if still generating
            # ------------------------------------------------

            generating = (
                await is_chatgpt_generating(
                    page
                )
            )

            if generating:

                continue

            # ------------------------------------------------
            # Wait briefly and read final response
            # ------------------------------------------------

            await asyncio.sleep(
                0.5
            )

            assistant_message = (
                await get_last_assistant_message(
                    page
                )
            )

            final_text = (
                await get_assistant_text(
                    assistant_message
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

                continue

            # ------------------------------------------------
            # Done
            # ------------------------------------------------

            print(
                "[CHATGPT] Generation finished."
            )

            yield (
                "data: [DONE]\n\n"
            )

            if newContext:

                try:

                    await page.close()

                except Exception as e:

                    print(
                        "[CHATGPT] Page close error: "
                        f"{e}"
                    )

            break

    except Exception as e:

        print(
            "\n"
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
# NON-STREAMING RESPONSE
# ============================================================

async def chatgpt_handle_response(
    page: Page,
    context,
    question: str,
) -> str:

    try:

        # ----------------------------------------------------
        # Ensure page
        # ----------------------------------------------------

        editor = await ensure_chatgpt_page(
            page
        )

        # ----------------------------------------------------
        # Submit
        # ----------------------------------------------------

        await submit_prompt(
            page,
            editor,
            question,
        )

        print(
            "[CHATGPT] Waiting for response..."
        )

        start_time = (
            asyncio.get_running_loop().time()
        )

        last_text = ""

        while True:

            elapsed = (
                asyncio.get_running_loop().time()
                - start_time
            )

            if elapsed > GENERATION_TIMEOUT:

                await save_debug_info(
                    page,
                    prefix="request-timeout",
                )

                raise RuntimeError(
                    "ChatGPT response timed out."
                )

            await asyncio.sleep(
                0.5
            )

            assistant_message = (
                await get_last_assistant_message(
                    page
                )
            )

            if assistant_message is None:

                continue

            current_text = (
                await get_assistant_text(
                    assistant_message
                )
            )

            if current_text:

                last_text = current_text

            generating = (
                await is_chatgpt_generating(
                    page
                )
            )

            if (
                last_text
                and not generating
            ):

                await asyncio.sleep(
                    0.5
                )

                assistant_message = (
                    await get_last_assistant_message(
                        page
                    )
                )

                final_text = (
                    await get_assistant_text(
                        assistant_message
                    )
                )

                if final_text:

                    last_text = final_text

                print(
                    "[CHATGPT] Generation finished."
                )

                return last_text

    except Exception as e:

        print(
            "\n"
            "[CHATGPT] Error while processing request:"
        )

        print(
            f"{type(e).__name__}: {e}"
        )

        try:

            await save_debug_info(
                page,
                prefix="request-error",
            )

        except Exception:
            pass

        return (
            "An error occurred while processing "
            "the request. Please try again later."
        )


# ============================================================
# TEST
# ============================================================

async def test_chatgpt(
    page: Page,
):

    print(
        "\n"
        + "=" * 70
    )

    print(
        "CHATGPT AUTOMATION TEST"
    )

    print(
        "=" * 70
    )

    try:

        editor = await ensure_chatgpt_page(
            page
        )

        print(
            "[TEST] SUCCESS"
        )

        print(
            "[TEST] Editor detected."
        )

        try:

            print(
                "[TEST] Tag:",
                await editor.evaluate(
                    "el => el.tagName"
                ),
            )

            print(
                "[TEST] ID:",
                await editor.get_attribute(
                    "id"
                ),
            )

        except Exception:
            pass

        return True

    except Exception as e:

        print(
            "[TEST] FAILED"
        )

        print(
            f"{type(e).__name__}: {e}"
        )

        return False
