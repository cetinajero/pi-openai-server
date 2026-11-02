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
   pip install fastapi uvicorn pydantic
   ```

---

## Running the Server

Start the server using Uvicorn via the virtual environment interpreter:

```bash
source venv/bin/activate
python3 server.py
```

The server will run at: `http://127.0.0.1:8000/v1`

---

## Integration with Hermes Agent

Add the following provider configuration to your Hermes configuration file (`~/.hermes/config.yaml`):

```yaml
providers:
  pi_local:
    base_url: "http://127.0.0.1:8000/v1"
    api_key: "not-needed"
    models:
      - pi/default
      - pi/sonnet
      - pi/gpt-4o
```

---

## API Endpoints

- **`GET /v1/models`**  
  Returns available models (`pi/default`, `pi/sonnet`, `pi/gpt-4o`).
- **`POST /v1/chat/completions`**  
  Accepts standard OpenAI chat completion payloads, translates them into `pi --no-session -p`, and returns the response (supports `stream: true`).

---

## License

MIT
