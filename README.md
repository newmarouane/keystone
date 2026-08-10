# GhostGPT 👻

> **GhostGPT** is a stealth, unauthenticated ChatGPT API bridge built with FastAPI and [Patchright](https://github.com/kaliiiiiiiiii/patchright-python) (an anti-detection Playwright fork). Operate ChatGPT quietly in the background without needing an API key!

---

## 🚀 Features

- 👻 **Ghost Engine**: Operates silently in the background via automated browser tabs without API keys or login.
- ⚡ **Real-Time SSE Streaming**: Stream responses chunk-by-chunk using Server-Sent Events (`/stream-ask`).
- 🍪 **Session Persistence**: Keeps track of multi-turn chat sessions automatically using HTTP cookies.
- 🥷 **Stealth Anti-Bot**: Powered by `patchright` to bypass automated browser detection.

---

## 📋 Prerequisites

- Python **3.13+** (or 3.10+)
- [`uv`](https://github.com/astral-sh/uv) *(recommended)* or standard `pip`

---

## 🏃 How to Run GhostGPT

### Option A: Using `uv` (Recommended)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/GhostGPT.git
   cd GhostGPT
   ```

2. **Sync dependencies & install Patchright Chromium browser**:
   ```bash
   uv sync
   uv run patchright install chromium
   ```

3. **Launch the server**:
   ```bash
   uv run uvicorn app:app --reload --port 8000
   ```

---

### Option B: Using standard Python (`pip` + `venv`)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/GhostGPT.git
   cd GhostGPT
   ```

2. **Create and activate a virtual environment**:
   - **Windows (PowerShell/CMD)**:
     ```powershell
     python -m venv .venv
     .venv\Scripts\activate
     ```
   - **Linux / macOS**:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. **Install dependencies and Chromium browser**:
   ```bash
   pip install fastapi patchright uvicorn
   patchright install chromium
   ```

4. **Launch the server**:
   ```bash
   uvicorn app:app --reload --port 8000
   ```

---

### 🌐 Accessing the API & Interactive Docs

Once running, the server initializes a stealth Chromium instance in the background.

- **API Server**: `http://localhost:8000`
- **Interactive Swagger Docs**: Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser to test endpoints directly from the Web UI!

---

### 🧪 Running Standalone Test Scripts

You can also run the standalone automation test scripts located in the `testing/` directory:

```bash
# Test ChatGPT browser automation directly
python testing/main.py

# Test Gemini browser automation directly
python testing/gemini.py
```

---

## 📡 API Reference

### 1. `POST /ask` (Standard JSON Response)
Sends a prompt to ChatGPT and returns the complete answer in a single JSON payload.

- **URL**: `/ask`
- **Method**: `POST`
- **Headers**: `Content-Type: application/json`
- **Body**:
  ```json
  {
    "question": "Explain quantum computing in simple terms.",
    "newContext": false
  }
  ```

#### Example `curl`:
```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello! Who are you?"}'
```

#### Example Response:
```json
{
  "response": "I'm ChatGPT, a large language model trained by OpenAI..."
}
```

---

### 2. `POST /stream-ask` (Streaming SSE)
Streams the ChatGPT response in real-time as a `text/event-stream`.

- **URL**: `/stream-ask`
- **Method**: `POST`
- **Headers**: `Content-Type: application/json`
- **Body**:
  ```json
  {
    "question": "Write a short poem about coding.",
    "newContext": false
  }
  ```

#### Example `curl`:
```bash
curl -N -X POST "http://localhost:8000/stream-ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Tell me a joke."}'
```

#### Stream Output Format:
```text
data: {"text": "Why do programmers..."}

data: {"text": "Why do programmers prefer dark mode?"}

data: [DONE]
```

---

## 📂 Project Structure

```text
GhostGPT/
├── app.py                 # FastAPI server & session management
├── browser.py             # Patchright browser engine setup
├── lib/
│   └── chatgpt.py         # ChatGPT DOM automation & response stream parsers
├── testing/               # Standalone test scripts (ChatGPT, Gemini)
│   ├── main.py            # ChatGPT standalone automation test
│   ├── gemini.py          # Gemini standalone automation test
│   └── test.py            # Event loop test utility
├── profile/               # Persistent browser session storage (git-ignored)
├── pyproject.toml         # Python dependencies & config
└── README.md              # Documentation
```

---

## ⚠️ Disclaimer

GhostGPT is built for educational, research, and testing purposes only. It relies on web browser automation and is not affiliated with or endorsed by OpenAI.
