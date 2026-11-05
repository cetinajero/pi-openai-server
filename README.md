# An OpenAI-compatible API server for Pi.dev

A lightweight FastAPI server that wraps the [Pi agent harness](https://pi.dev) and exposes an **OpenAI-compatible REST API**. 

This allows you to use Pi as a local provider in **Hermes Agent**, Aider, Cline, or any other OpenAI-compatible client.

## Features

- **OpenAI Standard API**: Supports standard chat completion requests (`/v1/chat/completions`) and model listing (`/v1/models`).
- **Streaming SSE**: Full support for real-time streaming chunk responses (`chat.completion.chunk`).
- **Ephemeral Sessions**: Uses `pi --no-session` to keep requests stateless and clean.
- **FastAPI + Uvicorn**: High performance, easy to run and extend.

---

## Installation & Setup

1. Clone or copy this repository:
   ```bash
   git clone https://github.com/cetinajero/pi-openai-server & cd pi-openai-server
   ```

2. Configure your desired models in `models.yml`:
   ```bash
   vi models.yml
   ```

3. Install as a system service (runs at boot via launchd):
   ```bash
   sudo ./pi-openai-server install
   ```

---

## Running & Managing the Server

You can manage the server using the `pi-openai-server` control script:

```bash
# Check status (running status and system service installation status)
pi-openai-server status

# Start the HTTP server
pi-openai-server start

# Stop the HTTP server
pi-openai-server stop

# Restart the HTTP server
pi-openai-server restart

# Install as a system service (runs at boot via launchd)
sudo pi-openai-server install

# Uninstall system service
sudo pi-openai-server uninstall

# Update to the latest version (pulls git repo, updates dependencies, updates symlink and restarts)
pi-openai-server update
```

The server runs at: `http://127.0.0.1:8000/v1`

---

## Integration with Hermes Agent

Use `hermes setup` or add the following provider configuration to your Hermes configuration file (`~/.hermes/config.yaml`):

```yaml
custom_providers: 
  - name: Pi OpenIA
    base_url: http://127.0.0.1:8000/v1
    model: pi/default
    models: {}
    models_discovered: false
```

---

## API Endpoints

- **`GET /v1/models`**  
  Returns available models.
- **`POST /v1/chat/completions`**  
  Accepts standard OpenAI chat completion payloads, translates them into `pi --no-session -p`, and returns the response (supports `stream: true`).

---

## License

MIT
