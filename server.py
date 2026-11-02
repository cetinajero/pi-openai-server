import os
import subprocess
import time
import sys
import json
from typing import List, Optional, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Pi OpenAI-Compatible API", version="1.0.0")

class ChatMessage(BaseModel):
    role: str
    content: Optional[str] = None

    class Config:
        extra = "allow"

class ChatCompletionRequest(BaseModel):
    model: str = "pi/default"
    messages: List[ChatMessage]
    stream: Optional[bool] = False

    class Config:
        extra = "allow"

@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "pi/default",
                "object": "model",
                "created": 1677610602,
                "owned_by": "pi"
            },
            {
                "id": "pi/sonnet",
                "object": "model",
                "created": 1677610602,
                "owned_by": "pi"
            },
            {
                "id": "pi/gpt-4o",
                "object": "model",
                "created": 1677610602,
                "owned_by": "pi"
            }
        ]
    }

@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest, raw_request: Request):
    try:
        body = await raw_request.json()
    except Exception:
        body = {}

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
        
    if req.model and req.model != "pi/default":
        model_name = req.model
        if model_name.startswith("pi/"):
            model_name = model_name[3:]
        cmd.extend(["--model", model_name])
        
    cmd.append(full_prompt)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180,
            env=os.environ.copy()
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error from pi"
            raise HTTPException(status_code=500, detail=f"Pi execution failed: {error_msg}")
            
        output_text = result.stdout.strip()
        
        # Handle streaming (SSE) if requested
        if req.stream:
            def event_generator():
                chunk_id = f"chatcmpl-{int(time.time())}"
                created = int(time.time())
                
                # Initial empty delta with role
                chunk_1 = {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": req.model,
                    "choices": [{"index": 0, "delta": {"role": "assistant", "content": ""}, "finish_reason": None}]
                }
                yield f"data: {json.dumps(chunk_1)}\n\n"
                
                # Stream content in chunks (words)
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
                    
                # Final finish reason chunk
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
        return {
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
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Pi execution timed out")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
