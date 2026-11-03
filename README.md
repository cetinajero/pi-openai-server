# An OpenAI-compatible API server for Pi.dev

A lightweight FastAPI server that wraps the **Pi coding assistant** (`pi --no-session`) and exposes an **OpenAI-compatible REST API** (`/v1/models` and `/v1/chat/completions`). 

This allows you to use Pi as a local provider in **Hermes Agent**, Aider, Cline, or any other OpenAI-compatible client.

## Features

- **OpenAI Standard API**: Supports standard chat completion requests (`/v1/chat/completions`) and model listing (`/v1/models`).
- **Streaming SSE**: Full support for real-time streaming chunk responses (`chat.completion.chunk`).
- **Ephemeral Sessions**: Uses `pi --no-session` to keep requests stateless and clean.
- **FastAPI + Uvicorn**: High performance, easy to run and extend.

---

## Installation & Setup

1. Clone or copy this repository to your projects directory:
   ```bash
   cd ~/projects/python/pi-openai-server
   ```

2. Create a Python virtual environment and install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install fastapi uvicorn pydantic
   ```

---

## Running & Managing the Server

You can manage the server using the `pi-openia-server` control script:

```bash
# Check status (running status and system service installation status)
pi-openia-server status

# Start the HTTP server
pi-openia-server start

# Stop the HTTP server
pi-openia-server stop

# Restart the HTTP server
pi-openia-server restart

# Install as a system service (runs at boot via launchd)
sudo pi-openia-server install

# Uninstall system service
sudo pi-openia-server uninstall
```

The server runs at: `http://127.0.0.1:8000/v1`

---

## Integration with Hermes Agent

Add the following provider configuration to your Hermes configuration file (`~/.hermes/config.yaml`):

```yaml
providers:
  pi_local:
    base_url: "http://127.0.0.1:8000/v1"
    api_key: "not-needed"
    models:
      - google/gemini-3.1-flash-lite (15/250/500)
      - google/gemini-3.5-flash-lite (15/250/500)
      - google/gemini-flash-lite-latest (15/250/500)
      - google/gemini-3.1-flash-lite-preview (15/250/500)
      - google/gemini-3.5-flash (5/250/20)
      - google/gemini-3.6-flash (5/250/20)
      - google/gemini-3.8-flash (5/250/20)
      - google/gemini-flash-latest (5/250/20)
      - google/gemini-3-flash-preview (5/250/20)
      - google/gemini-robotics-er-2-preview (5/250/20)
      - google/gemma-4-26b-a4b-it (30/16/14400)
      - google/gemma-4-31b-it (30/16/14400)
      - github/github-copilot-auto (200)
```

---

## API Endpoints

- **`GET /v1/models`**  
  Returns available models (`google/gemini-3.1-flash-lite (15/250/500)`, `google/gemini-3.5-flash-lite (15/250/500)`, `google/gemini-flash-lite-latest (15/250/500)`, `google/gemini-3.1-flash-lite-preview (15/250/500)`, `google/gemini-3.5-flash (5/250/20)`, `google/gemini-3.6-flash (5/250/20)`, `google/gemini-3.8-flash (5/250/20)`, `google/gemini-flash-latest (5/250/20)`, `google/gemini-3-flash-preview (5/250/20)`, `google/gemini-robotics-er-2-preview (5/250/20)`, `google/gemma-4-26b-a4b-it (30/16/14400)`, `google/gemma-4-31b-it (30/16/14400)`, `github/github-copilot-auto (200)`).
- **`POST /v1/chat/completions`**  
  Accepts standard OpenAI chat completion payloads, translates them into `pi --no-session -p`, and returns the response (supports `stream: true`).

---

## License

MIT
