from contextlib import asynccontextmanager
import uuid
from fastapi import FastAPI,Response, Cookie
from fastapi.responses import StreamingResponse
from patchright.async_api import Page
from pydantic import BaseModel
from browser import  start_browser,create_new_page
from lib.chatgpt import chatgpt_handle_response, stream_chatgpt_response
import asyncio
import sys
from fastapi.staticfiles import StaticFiles
from pathlib import Path

Path("/app/debug").mkdir(
    parents=True,
    exist_ok=True,
)
app = FastAPI()

app.mount(
    "/debug",
    StaticFiles(directory="/app/debug"),
    name="debug",
)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
# browser = None
playwright = None
context = None
page = None
active_sessions: dict[str, Page] = {}
@asynccontextmanager
async def lifespan(app: FastAPI):
    global playwright, context, page
    playwright, context, page = await start_browser()
    yield
    await context.close()
    await playwright.stop()
app = FastAPI(lifespan=lifespan)
@app.get("/")
async def root():
    return {"message": "Hello World"}
class QuestionRequest(BaseModel):
    question: str
    newContext: bool | None = False
@app.post("/ask")
async def ask_question(data: QuestionRequest,response: Response,user_session_id:str | None = Cookie(default=None)):
    question = data.question
    if(not question):
        return {"error": "Question is required"}
    page = await handle_user_session(user_session_id,data.newContext,response)
    content = await chatgpt_handle_response(page, context, question)
    if data.newContext:
        await page.close()
    return {"response": content}

@app.post("/stream-ask")
async def stream_ask(data: QuestionRequest, response: Response, user_session_id: str | None = Cookie(default=None)):
    page = await handle_user_session(user_session_id, data.newContext, response)
    if not page:
        return {"error": "Session not found. Please initialize session first."}
    # Return a StreamingResponse running your async generator
    return StreamingResponse(
        stream_chatgpt_response(page, data.question, data.newContext),
        media_type="text/event-stream"
    )


async def handle_user_session(user_session_id: str | None,newContext: bool, response: Response):
      if(not newContext):
            if user_session_id is None or user_session_id not in active_sessions:
                user_session_id = str(uuid.uuid4())
                response.set_cookie(key="user_session_id", value=user_session_id, max_age=3600)
                new_page = await create_new_page(context)
                active_sessions[user_session_id] = new_page
            page = active_sessions[user_session_id]
      else:
            page = await create_new_page(context)
      return page
