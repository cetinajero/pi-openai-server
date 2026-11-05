import os
import subprocess
import time
import sys
import json
from contextlib import asynccontextmanager
import logging
from typing import List, Optional, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
import uvicorn

# Setup logs directory
LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Configure agent logger for requests and responses
agent_logger = logging.getLogger("agent_activity")
agent_logger.setLevel(logging.INFO)
agent_handler = logging.FileHandler(os.path.join(LOGS_DIR, "agent.log"))
agent_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
if not agent_logger.handlers:
    agent_logger.addHandler(agent_handler)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Clear agent.log on startup, keep server.log intact
    agent_log_path = os.path.join(LOGS_DIR, "agent.log")
    try:
        open(agent_log_path, "w").close()
    except Exception:
        pass
    yield

app = FastAPI(title="Pi OpenAI-Compatible API", version="1.0.0", lifespan=lifespan)

class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="allow")
    role: str
    content: Optional[str] = None

class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    model: str = "gemini-flash-lite-latest (15-250-500)"
    messages: List[ChatMessage]
    stream: Optional[bool] = False

def load_models():
    models_path = os.path.join(os.path.dirname(__file__), "models.yml")
    models = []
    try:
        with open(models_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("models:"):
                    continue
                if "{" in line and "}" in line:
                    content = line[line.find("{")+1 : line.find("}")]
                    parts = [p.strip() for p in content.split(",")]
                    m = {}
                    for p in parts:
                        if ":" in p:
                            k, v = p.split(":", 1)
                            m[k.strip()] = v.strip().strip('"').strip("'")
                    if "id" in m and "rate_limits" in m:
                        models.append(m)
    except Exception:
        pass
        
    formatted_models = []
    for m in models:
        full_id = f"{m['id']} ({m['rate_limits']})"
        formatted_models.append({"id": full_id, "owned_by": m.get("owned_by", "pi")})
    return formatted_models

@app.get("/v1/models")
async def list_models():
    models = load_models()
    return {
        "object": "list",
        "data": [
            {
                "id": m["id"],
                "object": "model",
                "created": 1677610602,
                "owned_by": m.get("owned_by", "pi")
            }
            for m in models
        ]
    }

@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest, raw_request: Request):
    try:
        req_body = await raw_request.json()
    except Exception:
        req_body = {}

    agent_logger.info(f"--- INCOMING REQUEST ---")
    agent_logger.info(json.dumps(req_body, ensure_ascii=False))

    system_prompt = None
    prompt_parts = []
    
    for msg in req.messages:
        role = msg.role
        content = msg.content or ""
        if role == "system":
            system_prompt = content
        elif role == "user":
            prompt_parts.append(f"User: {content}")
        elif role == "assistant":
            prompt_parts.append(f"Assistant: {content}")
        elif role == "tool":
            prompt_parts.append(f"Tool Result: {content}")
            
    if not prompt_parts:
        prompt_parts.append("User: Hello")
        
    full_prompt = "\n\n".join(prompt_parts)
    
    cmd = ["pi", "--no-session", "-p"]
    if system_prompt:
        cmd.extend(["--system-prompt", system_prompt])
        
    models = load_models()
    default_model = models[0]["id"] if models else "gemini-flash-lite-latest (15-250-500)"
    model_name = req.model or default_model
    if " (" in model_name:
        model_name = model_name.split(" (")[0]
    cmd.extend(["--model", model_name])
        
    cmd.append(full_prompt)
    
    try:
        env = os.environ.copy()
        extra_paths = ["/opt/homebrew/bin", "/usr/local/bin", "/Users/cetinajero/.pi/agent/bin"]
        current_path = env.get("PATH", "")
        for p in extra_paths:
            if p not in current_path:
                current_path = f"{p}:{current_path}"
        env["PATH"] = current_path

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180,
            env=env
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error from pi"
            agent_logger.error(f"Pi execution failed: {error_msg}")
            raise HTTPException(status_code=500, detail=f"Pi execution failed: {error_msg}")
            
        output_text = result.stdout.strip()
        
        # Handle streaming (SSE) if requested
        if req.stream:
            resp_obj = {
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": req.model,
                "choices": [{"index": 0, "message": {"role": "assistant", "content": output_text}, "finish_reason": "stop"}]
            }
            agent_logger.info(f"--- OUTGOING STREAMING RESPONSE ---")
            agent_logger.info(json.dumps(resp_obj, ensure_ascii=False))

            def event_generator():
                chunk_id = f"chatcmpl-{int(time.time())}"
                created = int(time.time())
                
                chunk_1 = {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": req.model,
                    "choices": [{"index": 0, "delta": {"role": "assistant", "content": ""}, "finish_reason": None}]
                }
                yield f"data: {json.dumps(chunk_1)}\n\n"
                
                words = output_text.split(" ")
                for i, word in enumerate(words):
                    piece = word + (" " if i < len(words) - 1 else "")
                    chunk_piece = {
                        "id": chunk_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": req.model,
                        "choices": [{"index": 0, "delta": {"content": piece}, "finish_reason": None}]
                    }
                    yield f"data: {json.dumps(chunk_piece)}\n\n"
                    time.sleep(0.01)
                    
                chunk_end = {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": req.model,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
                }
                yield f"data: {json.dumps(chunk_end)}\n\n"
                yield "data: [DONE]\n\n"

            return StreamingResponse(event_generator(), media_type="text/event-stream")
        
        # Non-streaming response
        resp_obj = {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": req.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": output_text
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": len(full_prompt.split()),
                "completion_tokens": len(output_text.split()),
                "total_tokens": len(full_prompt.split()) + len(output_text.split())
            }
        }
        agent_logger.info(f"--- OUTGOING RESPONSE ---")
        agent_logger.info(json.dumps(resp_obj, ensure_ascii=False))

        return resp_obj
    except subprocess.TimeoutExpired:
        agent_logger.error("Pi execution timed out")
        raise HTTPException(status_code=504, detail="Pi execution timed out")
    except Exception as e:
        agent_logger.error(f"Exception: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    from uvicorn.config import LOGGING_CONFIG

    print("-" * 60, flush=True)

    log_config = LOGGING_CONFIG.copy()
    log_config["formatters"]["access"]["fmt"] = "%(asctime)s %(levelname)s %(client_addr)s - \"%(request_line)s\" %(status_code)s"
    log_config["formatters"]["default"]["fmt"] = "%(asctime)s %(levelname)s %(message)s"

    uvicorn.run(app, host="127.0.0.1", port=8000, log_config=log_config)
