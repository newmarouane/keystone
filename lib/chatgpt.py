import asyncio
import json
async def chatgpt_handle_response(page,context,question) -> str:
    try:
        if(page.url != "https://chatgpt.com/"):
            await page.goto(
                "https://chatgpt.com/",
                wait_until="domcontentloaded"
            )
        print(page.url)
        # await page.screenshot(path="debug.png")
        editor = page.locator("#prompt-textarea")
        await editor.wait_for(state="visible")
        await editor.click()
        await editor.press_sequentially(question)
        await editor.press("Enter")
        stop_button = page.get_by_role("button", name="Stop answer")
        await stop_button.wait_for(state="visible")
        await stop_button.wait_for(state="hidden")
        print("Generation finished for stop button")
        await page.get_by_role("button", name="Copy response").last.evaluate("node => node.click()")
        # await copy_button.wait_for(state="visible")
        print("Generation finished")
        # await copy_button.scroll_into_view_if_needed()
        # await copy_button.click()
        text = await page.evaluate("""
        async () => {
            return await navigator.clipboard.readText();
        }
        """)
    except Exception as e:
        print(e)
        return "An error occurred while processing the request. Please try again later."
    finally:
        # await context.close()
        return text    


async def stream_chatgpt_response(page, prompt: str, newContext: bool):
    if page.url != "https://chatgpt.com/":
        await page.goto("https://chatgpt.com/", wait_until="domcontentloaded")
        
    print(f"Current URL: {page.url}")
    
    editor = page.locator("#prompt-textarea")
    await editor.wait_for(state="visible")
    await editor.click()
    await editor.press_sequentially(prompt)
    await editor.press("Enter")
    
    await asyncio.sleep(1.0)
    
    last_text = ""
    has_started_generating = False # FIX 3: Flag to prevent early exits
    while True:
        await asyncio.sleep(0.2)
        try:
            # FIX 1: Add .markdown back so we ONLY get the text, not the buttons/thinking UI
            assistant_message = page.locator('[data-message-author-role="assistant"] .markdown').last
            current_text = await assistant_message.inner_text()
        except Exception:
            continue
            
        # FIX 2: Compare the actual text instead of lengths to avoid slice corruption
        if current_text != last_text:
            has_started_generating = True 
            
            # FIX 3: Package the FULL text in JSON. 
            # This safely escapes raw \n into literal \\n so the SSE stream doesn't break.
            payload = json.dumps({"text": current_text})
            yield f"data: {payload}\n\n"
            
            last_text = current_text
            
        else:
            if has_started_generating:
                is_done = await page.evaluate("""
                    () => {
                        return !document.querySelector('button[aria-label="Stop answer"]');
                    }
                """)

                if is_done:
                    current_text = await assistant_message.inner_text()
                    if current_text != last_text:
                        continue
                    print("Generation finished")
                    yield "data: [DONE]\n\n"
                    if newContext:
                        await page.close()
                    break


# ------------------------------ This one also works but has some issues ------------------------------
#   while True:
#         await asyncio.sleep(0.2)
        
#         try:
#             # FIX 4: Removed the redundant .last on the second line
#             assistant_message = page.locator('[data-message-author-role="assistant"]')
#             current_text = await assistant_message.last.inner_text()
#             print(current_text)
#         except Exception:
#             # If element doesn't exist yet, keep looping
#             continue
            
#         if len(current_text) > last_length:
#             has_started_generating = True # Text has officially started flowing
#             new_text = current_text[last_length:]
#             payload = json.dumps({"text": current_text})
#             yield f"data: {new_text}\n\n"
#             last_length = len(current_text)
            
#         else:
#             # FIX 3 (continued): Only check if it's done IF generation actually started.
#             # This prevents the stream from closing if the network is just slow to start.
#             if has_started_generating:
#                 is_done = await page.evaluate("""
#                     () => {
#                         return !document.querySelector('button[aria-label="Stop answer"]');
#                     }
#                 """)
                
#                 if is_done:
#                     current_text = await assistant_message.last.inner_text()
#                     if len(current_text) > last_length:
#                         continue
#                     print("Generation finished")
#                     yield "data: [DONE]\n\n"
#                     break