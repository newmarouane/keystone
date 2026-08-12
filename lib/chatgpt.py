import asyncio
import json


CHATGPT_URL = "https://chatgpt.com/"


async def ensure_chatgpt_page(page):
    if not page.url.startswith("https://chatgpt.com"):
        await page.goto(
            "https://chatgpt.com/",
            wait_until="domcontentloaded",
        )

    print(f"Current ChatGPT URL: {page.url}")

    title = ""
    try:
        title = await page.title()
    except Exception:
        pass

    print(f"Page title: {title}")

    # Detect Cloudflare by URL OR page title.
    if (
        "__cf_chl" in page.url
        or "just a moment" in title.lower()
    ):
        raise RuntimeError(
            f"Cloudflare challenge detected. "
            f"URL: {page.url}, Title: {title}"
        )

    editor = page.locator("#prompt-textarea")

    try:
        await editor.wait_for(
            state="visible",
            timeout=30000,
        )
    except Exception as e:
        print("ChatGPT editor was not found.")
        print(e)
        print(f"Current URL: {page.url}")
        print(f"Page title: {title}")

        raise RuntimeError(
            f"ChatGPT interface did not load. "
            f"URL: {page.url}, Title: {title}"
        ) from e

    return editor


async def chatgpt_handle_response(
    page,
    context,
    question,
) -> str:

    try:
        editor = await ensure_chatgpt_page(page)

        await editor.click()
        await editor.press_sequentially(question)
        await editor.press("Enter")

        # Wait for generation to start.
        stop_button = page.get_by_role(
            "button",
            name="Stop answer",
        )

        try:
            await stop_button.wait_for(
                state="visible",
                timeout=30000,
            )

            # Wait until generation finishes.
            await stop_button.wait_for(
                state="hidden",
                timeout=300000,
            )

        except Exception:
            print(
                "Stop answer button was not detected or disappeared."
            )

        print("Generation finished for stop button")

        # Wait for the Copy response button.
        copy_button = page.get_by_role(
            "button",
            name="Copy response",
        ).last

        await copy_button.wait_for(
            state="visible",
            timeout=30000,
        )

        await copy_button.evaluate(
            "node => node.click()"
        )

        print("Generation finished")

        # Read the copied response.
        text = await page.evaluate(
            """
            async () => {
                return await navigator.clipboard.readText();
            }
            """
        )

        return text or ""

    except Exception as e:
        print(e)
        print(
            f"Error while processing ChatGPT request: "
            f"{type(e).__name__}: {e}"
        )

        # Do NOT use "finally: return text".
        # text may not exist when an exception occurs.
        return (
            "An error occurred while processing the request. "
            "Please try again later."
        )


async def stream_chatgpt_response(
    page,
    prompt: str,
    newContext: bool,
):
    try:
        editor = await ensure_chatgpt_page(page)

        await editor.click()
        await editor.press_sequentially(prompt)
        await editor.press("Enter")

        await asyncio.sleep(1.0)

        last_text = ""
        has_started_generating = False

        while True:

            await asyncio.sleep(0.2)

            try:
                assistant_message = page.locator(
                    '[data-message-author-role="assistant"] .markdown'
                ).last

                current_text = await assistant_message.inner_text()

            except Exception:
                continue

            # New content arrived.
            if current_text != last_text:

                has_started_generating = True

                payload = json.dumps(
                    {"text": current_text},
                    ensure_ascii=False,
                )

                yield f"data: {payload}\n\n"

                last_text = current_text

                continue

            # Don't check for completion before generation starts.
            if not has_started_generating:
                continue

            try:
                is_done = await page.evaluate(
                    """
                    () => {
                        return !document.querySelector(
                            'button[aria-label="Stop answer"]'
                        );
                    }
                    """
                )

            except Exception:
                continue

            if is_done:

                # One final read in case the response changed
                # between our previous check and completion.
                try:
                    final_text = await assistant_message.inner_text()
                except Exception:
                    final_text = last_text

                if final_text != last_text:

                    payload = json.dumps(
                        {"text": final_text},
                        ensure_ascii=False,
                    )

                    yield f"data: {payload}\n\n"

                    last_text = final_text

                    continue

                print("Generation finished")

                yield "data: [DONE]\n\n"

                if newContext:
                    try:
                        await page.close()
                    except Exception as e:
                        print(
                            f"Error closing page: {e}"
                        )

                break

    except Exception as e:

        print(
            f"Streaming error: "
            f"{type(e).__name__}: {e}"
        )

        # Send an SSE-compatible error instead of crashing
        # the generator.
        payload = json.dumps(
            {
                "error": (
                    "An error occurred while processing "
                    "the ChatGPT request."
                )
            },
            ensure_ascii=False,
        )

        yield f"data: {payload}\n\n"
        yield "data: [DONE]\n\n"
