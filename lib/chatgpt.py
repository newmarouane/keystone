import asyncio
import json
import os
import time
from pathlib import Path

from playwright.async_api import (
    Page,
    TimeoutError as PlaywrightTimeoutError,
)


CHATGPT_URL = "https://chatgpt.com/"

EDITOR_TIMEOUT = 60_000
PAGE_LOAD_TIMEOUT = 60_000
GENERATION_TIMEOUT = 300  # seconds

DEBUG_DIR = Path("/tmp/chatgpt-debug")
DEBUG_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# DEBUG HELPERS
# ============================================================

async def save_debug_info(page: Page, prefix: str = "chatgpt"):
    """
    Save screenshot + HTML + visible body text for diagnostics.
    """

    timestamp = int(time.time())

    screenshot_path = (
        DEBUG_DIR / f"{prefix}-{timestamp}.png"
    )

    html_path = (
        DEBUG_DIR / f"{prefix}-{timestamp}.html"
    )

    body_path = (
        DEBUG_DIR / f"{prefix}-{timestamp}.txt"
    )

    # Screenshot
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
            f"[DEBUG] Could not save screenshot: {e}"
        )

    # HTML
    try:
        html = await page.content()

        html_path.write_text(
            html,
            encoding="utf-8",
        )

        print(
            f"[DEBUG] HTML saved: {html_path}"
        )

    except Exception as e:
        print(
            f"[DEBUG] Could not save HTML: {e}"
        )

    # Body text
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
            f"[DEBUG] Body text saved: {body_path}"
        )

        print(
            "[DEBUG] Body preview:\n"
            + body_text[:3000]
        )

    except Exception as e:
        print(
            f"[DEBUG] Could not read body: {e}"
        )


# ============================================================
# BROWSER / PAGE DIAGNOSTICS
# ============================================================

async def print_page_diagnostics(page: Page):

    print("=" * 70)
    print("CHATGPT PAGE DIAGNOSTICS")
    print("=" * 70)

    print(f"URL: {page.url}")

    try:
        title = await page.title()
    except Exception:
        title = ""

    print(f"TITLE: {title!r}")

    try:
        body_text = await page.locator(
            "body"
        ).inner_text(
            timeout=5000
        )

        print(
            "BODY:\n"
            + body_text[:3000]
        )

    except Exception as e:
        print(
            f"Could not read body: {e}"
        )

    print("=" * 70)


# ============================================================
# CLOUDFLARE / SECURITY DETECTION
# ============================================================

async def detect_security_challenge(page: Page):

    url = page.url.lower()

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

    url_indicators = [
        "__cf_chl",
        "challenge-platform",
        "cdn-cgi/challenge",
        "cf-chl",
    ]

    html_indicators = [
        "just a moment",
        "checking your browser",
        "verify you are human",
        "performing security verification",
        "challenge-platform",
        "cf-chl",
        "cloudflare",
    ]

    url_match = any(
        indicator in url
        for indicator in url_indicators
    )

    html_match = any(
        indicator in html
        for indicator in html_indicators
    )

    if url_match or html_match:

        await save_debug_info(
            page,
            prefix="security-challenge",
        )

        raise RuntimeError(
            "Cloudflare/security challenge detected.\n"
            f"URL: {page.url}\n"
            f"Title: {title!r}"
        )


# ============================================================
# AUTHENTICATION DIAGNOSTICS
# ============================================================

async def inspect_authentication(page: Page):

    print("[AUTH] Inspecting browser session...")

    try:
        cookies = (
            await page.context.cookies()
        )

        print(
            f"[AUTH] Browser has "
            f"{len(cookies)} cookies."
        )

        # Don't print cookie values.
        for cookie in cookies:
            domain = cookie.get(
                "domain",
                ""
            )

            name = cookie.get(
                "name",
                ""
            )

            if (
                "chatgpt" in domain.lower()
                or "openai" in domain.lower()
            ):
                print(
                    f"[AUTH] Cookie: "
                    f"{name} @ {domain}"
                )

    except Exception as e:
        print(
            f"[AUTH] Cookie inspection failed: {e}"
        )


# ============================================================
# FIND CHATGPT EDITOR
# ============================================================

async def get_chatgpt_editor(page: Page):

    selectors = [
        "#prompt-textarea",
        "textarea[placeholder*='Message']",
        "textarea",
        "[contenteditable='true']",
    ]

    print(
        "[EDITOR] Searching for ChatGPT composer..."
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
                f"[EDITOR] Found editor using: "
                f"{selector}"
            )

            return locator

        except Exception:
            pass

    raise RuntimeError(
        "Could not find ChatGPT message editor."
    )


# ============================================================
# ENSURE CHATGPT PAGE
# ============================================================

async def ensure_chatgpt_page(page: Page):

    print(
        "[CHATGPT] Ensuring ChatGPT page..."
    )

    # --------------------------------------------------------
    # Navigate if necessary
    # --------------------------------------------------------

    if not page.url.startswith(
        CHATGPT_URL
    ):

        print(
            f"[CHATGPT] Navigating to "
            f"{CHATGPT_URL}"
        )

        await page.goto(
            CHATGPT_URL,
            wait_until="domcontentloaded",
            timeout=PAGE_LOAD_TIMEOUT,
        )

    else:

        print(
            "[CHATGPT] Already on ChatGPT URL."
        )

    print(
        f"[CHATGPT] Current URL: "
        f"{page.url}"
    )

    # --------------------------------------------------------
    # Wait for page load
    # --------------------------------------------------------

    try:

        await page.wait_for_load_state(
            "networkidle",
            timeout=20_000,
        )

        print(
            "[CHATGPT] Network idle reached."
        )

    except PlaywrightTimeoutError:

        print(
            "[CHATGPT] Network idle timeout. "
            "Continuing..."
        )

    # --------------------------------------------------------
    # Give React/frontend time to initialize
    # --------------------------------------------------------

    await asyncio.sleep(2)

    # --------------------------------------------------------
    # Basic diagnostics
    # --------------------------------------------------------

    try:
        title = await page.title()
    except Exception:
        title = ""

    print(
        f"[CHATGPT] Title: {title!r}"
    )

    print(
        f"[CHATGPT] Final URL: "
        f"{page.url}"
    )

    # --------------------------------------------------------
    # Security challenge detection
    # --------------------------------------------------------

    await detect_security_challenge(
        page
    )

    # --------------------------------------------------------
    # Authentication diagnostics
    # --------------------------------------------------------

    await inspect_authentication(
        page
    )

    # --------------------------------------------------------
    # Try to find editor
    # --------------------------------------------------------

    try:

        editor = await get_chatgpt_editor(
            page
        )

        print(
            "[CHATGPT] Editor found successfully."
        )

        return editor

    except Exception as editor_error:

        print(
            "[CHATGPT] Editor was not found."
        )

        print(
            f"[CHATGPT] Error: "
            f"{editor_error}"
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
            f"Original error: {editor_error}"
        ) from editor_error


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

    # fill() is more reliable than
    # press_sequentially() for long prompts.
    try:

        await editor.fill(
            prompt
        )

    except Exception:

        # Fallback for contenteditable
        await editor.press_sequentially(
            prompt,
            delay=2,
        )

    await asyncio.sleep(0.2)

    await editor.press(
        "Enter"
    )

    print(
        "[CHATGPT] Prompt submitted."
    )


# ============================================================
# FIND ASSISTANT MESSAGE
# ============================================================

async def get_last_assistant_message(page: Page):

    selectors = [

        '[data-message-author-role="assistant"]',

        '[data-message-author-role="assistant"] .markdown',

        'article[data-testid*="conversation-turn"]',

    ]

    for selector in selectors:

        try:

            locator = page.locator(
                selector
            ).last

            count = await page.locator(
                selector
            ).count()

            if count == 0:
                continue

            await locator.wait_for(
                state="visible",
                timeout=3000,
            )

            return locator

        except Exception:
            continue

    return None


# ============================================================
# GET CURRENT ASSISTANT TEXT
# ============================================================

async def get_assistant_text(
    page: Page,
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
# CHECK WHETHER CHATGPT IS GENERATING
# ============================================================

async def is_chatgpt_generating(page: Page):

    selectors = [

        'button[aria-label="Stop answer"]',

        'button[aria-label="Stop generating"]',

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
# STREAM CHATGPT RESPONSE
# ============================================================

async def stream_chatgpt_response(
    page: Page,
    prompt: str,
    newContext: bool,
):

    try:

        # ----------------------------------------------------
        # Make sure ChatGPT is loaded
        # ----------------------------------------------------

        editor = await ensure_chatgpt_page(
            page
        )

        # ----------------------------------------------------
        # Submit prompt
        # ----------------------------------------------------

        await submit_prompt(
            page,
            editor,
            prompt,
        )

        # ----------------------------------------------------
        # Wait briefly for assistant message
        # ----------------------------------------------------

        await asyncio.sleep(1)

        last_text = ""

        has_started_generating = False

        generation_start = (
            asyncio.get_running_loop().time()
        )

        assistant_message = None

        # ----------------------------------------------------
        # Streaming loop
        # ----------------------------------------------------

        while True:

            # -----------------------------------------------
            # Global timeout
            # -----------------------------------------------

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

            await asyncio.sleep(0.2)

            # -----------------------------------------------
            # Find assistant response
            # -----------------------------------------------

            try:

                assistant_message = (
                    await get_last_assistant_message(
                        page
                    )
                )

            except Exception:
                assistant_message = None

            if assistant_message is None:

                # Don't immediately consider the
                # generation finished.
                continue

            # -----------------------------------------------
            # Read current response
            # -----------------------------------------------

            current_text = (
                await get_assistant_text(
                    page,
                    assistant_message,
                )
            )

            if not current_text:

                continue

            # -----------------------------------------------
            # New content arrived
            # -----------------------------------------------

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

            # -----------------------------------------------
            # Don't check completion before generation starts
            # -----------------------------------------------

            if not has_started_generating:

                continue

            # -----------------------------------------------
            # Check generation state
            # -----------------------------------------------

            try:

                generating = (
                    await is_chatgpt_generating(
                        page
                    )
                )

            except Exception:

                generating = True

            if generating:

                continue

            # -----------------------------------------------
            # Generation appears finished
            # -----------------------------------------------

            await asyncio.sleep(
                0.5
            )

            # Read one final time.
            try:

                assistant_message = (
                    await get_last_assistant_message(
                        page
                    )
                )

                final_text = (
                    await get_assistant_text(
                        page,
                        assistant_message,
                    )
                )

            except Exception:

                final_text = last_text

            # -----------------------------------------------
            # Final content changed
            # -----------------------------------------------

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

                # Give frontend another moment
                continue

            # -----------------------------------------------
            # Finished
            # -----------------------------------------------

            print(
                "[CHATGPT] Generation finished."
            )

            yield (
                "data: [DONE]\n\n"
            )

            # -----------------------------------------------
            # Close temporary context/page
            # -----------------------------------------------

            if newContext:

                try:

                    await page.close()

                except Exception as e:

                    print(
                        "[CHATGPT] Error closing page: "
                        f"{e}"
                    )

            break

    except Exception as e:

        print(
            "[CHATGPT] Streaming error:"
        )

        print(
            f"{type(e).__name__}: {e}"
        )

        # Save diagnostics
        try:

            await save_debug_info(
                page,
                prefix="stream-error",
            )

        except Exception:
            pass

        # SSE-compatible error
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
        # Submit prompt
        # ----------------------------------------------------

        await submit_prompt(
            page,
            editor,
            question,
        )

        # ----------------------------------------------------
        # Wait for assistant response
        # ----------------------------------------------------

        print(
            "[CHATGPT] Waiting for response..."
        )

        start_time = (
            asyncio.get_running_loop().time()
        )

        assistant_message = None
        last_text = ""

        while True:

            elapsed = (
                asyncio.get_running_loop().time()
                - start_time
            )

            if elapsed > GENERATION_TIMEOUT:

                raise RuntimeError(
                    "ChatGPT response timed out."
                )

            await asyncio.sleep(0.5)

            assistant_message = (
                await get_last_assistant_message(
                    page
                )
            )

            if assistant_message is None:

                continue

            current_text = (
                await get_assistant_text(
                    page,
                    assistant_message,
                )
            )

            if current_text:

                last_text = current_text

            # Wait until generation is finished
            generating = (
                await is_chatgpt_generating(
                    page
                )
            )

            if (
                last_text
                and not generating
            ):

                # One final read
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
                        page,
                        assistant_message,
                    )
                )

                if final_text:
                    last_text = final_text

                break

        print(
            "[CHATGPT] Generation finished."
        )

        return last_text or ""

    except Exception as e:

        print(
            "[CHATGPT] Error while processing "
            "request:"
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
# OPTIONAL TEST FUNCTION
# ============================================================

async def test_chatgpt(page: Page):

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
            "\nSUCCESS: ChatGPT editor detected."
        )

        print(
            "Editor tag:",
            await editor.evaluate(
                "el => el.tagName"
            ),
        )

        print(
            "Editor id:",
            await editor.get_attribute(
                "id"
            ),
        )

        return True

    except Exception as e:

        print(
            "\nFAILED:"
        )

        print(
            f"{type(e).__name__}: {e}"
        )

        return False
