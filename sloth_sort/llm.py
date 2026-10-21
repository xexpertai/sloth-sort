"""Client for a local llama.cpp server (OpenAI-compatible). Talks to 127.0.0.1 only by default."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

DEFAULT_URL = os.environ.get("SLOTH_LLM_URL", "http://127.0.0.1:8187")


class LLMUnavailable(RuntimeError):
    pass


def available(url: str = DEFAULT_URL) -> bool:
    try:
        with urllib.request.urlopen(f"{url}/health", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def model_name(url: str = DEFAULT_URL) -> str:
    try:
        with urllib.request.urlopen(f"{url}/v1/models", timeout=3) as r:
            return os.path.basename(json.load(r)["data"][0]["id"]).removesuffix(".gguf")
    except Exception:
        return "unknown"


def chat(messages: list[dict], schema: dict, *, url: str = DEFAULT_URL, max_tokens: int = 120,
         seed: int = 7, timeout: float = 300) -> tuple[dict, float]:
    body = {"messages": messages, "max_tokens": max_tokens, "temperature": 0.0, "seed": seed,
            "response_format": {"type": "json_schema", "json_schema": {"name": "out", "schema": schema}}}
    req = urllib.request.Request(f"{url}/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
    except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as e:
        raise LLMUnavailable(str(e)) from e
    text = data["choices"][0]["message"].get("content") or "{}"
    return json.loads(text), round(time.time() - t0, 1)
