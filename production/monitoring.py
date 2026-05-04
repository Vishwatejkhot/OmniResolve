import os
from functools import wraps
from typing import Any, Callable

_tracing_enabled = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"

def _get_client():
    if not _tracing_enabled:
        return None
    try:
        from langsmith import Client
        return Client()
    except Exception:
        return None

_client = _get_client()

def trace_node(node_name: str):
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        async def wrapper(state: Any) -> Any:
            if _client is None:
                return await fn(state)

            from langsmith import traceable

            @traceable(name=node_name, run_type="chain")
            async def _traced(*args, **kwargs):
                return await fn(*args, **kwargs)

            return await _traced(state)

        return wrapper
    return decorator

def get_run_url(run_id: str) -> str | None:
    if _client is None:
        return None
    try:
        run = _client.read_run(run_id)
        return run.url
    except Exception:
        return None

def log_feedback(run_id: str, score: float, comment: str = "") -> None:
    if _client is None:
        return
    try:
        _client.create_feedback(run_id=run_id, key="resolution_quality", score=score, comment=comment)
    except Exception:
        pass
