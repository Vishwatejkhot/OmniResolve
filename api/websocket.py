import json
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from channels.chat_handler import normalise_chat_message, extract_state_hints
from channels.document_handler import build_documents_from_attachments

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active: dict[str, WebSocket] = {}

    async def connect(self, case_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self.active[case_id] = ws

    def disconnect(self, case_id: str) -> None:
        self.active.pop(case_id, None)

    async def send(self, case_id: str, data: dict) -> None:
        ws = self.active.get(case_id)
        if ws:
            await ws.send_text(json.dumps(data))

manager = ConnectionManager()

@router.websocket("/ws/chat/{case_id}")
async def chat_endpoint(websocket: WebSocket, case_id: str):
    await manager.connect(case_id, websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            payload = json.loads(raw)

            event = normalise_chat_message(payload)
            hints = extract_state_hints(payload)

            from agents.orchestrator import get_compiled_graph

            graph = await get_compiled_graph()
            config = {"configurable": {"thread_id": case_id}}
            state_snapshot = await graph.aget_state(config)

            if state_snapshot and state_snapshot.values:
                existing_history = state_snapshot.values.get("channel_history", [])
                await graph.aupdate_state(config, {
                    "channel_history": existing_history + [event],
                    "_raw_events": [payload],
                    **hints,
                })
                final = await graph.ainvoke(None, config=config)
            else:
                initial = {
                    "case_id": case_id,
                    "customer_id": hints.get("customer_id", ""),
                    "order_id": hints.get("order_id", ""),
                    "session_id": hints.get("session_id", case_id),
                    "channel_history": [],
                    "documents": [],
                    "evidence_scores": {},
                    "dispute_category": "",
                    "policy_findings": [],
                    "legal_citations": [],
                    "precedent_cases": [],
                    "graph_subgraph": {},
                    "resolution_recommendation": "",
                    "confidence_score": 0.0,
                    "requires_human": False,
                    "cache_key": "",
                    "retry_count": 0,
                    "error_log": [],
                    "_raw_events": [payload],
                }
                final = await graph.ainvoke(initial, config=config)

            await manager.send(case_id, {
                "type": "resolution",
                "case_id": case_id,
                "resolution": final.get("resolution_recommendation"),
                "confidence": final.get("confidence_score"),
                "requires_human": final.get("requires_human"),
                "legal_citations": final.get("legal_citations", []),
                "brief": final.get("graph_subgraph", {}).get("resolution_brief", ""),
            })

    except WebSocketDisconnect:
        manager.disconnect(case_id)

@router.websocket("/ws/voice/{case_id}")
async def voice_endpoint(websocket: WebSocket, case_id: str):
    await websocket.accept()
    try:
        while True:
            audio_bytes = await websocket.receive_bytes()
            from channels.voice_handler import handle_voice_upload
            event = await handle_voice_upload(audio_bytes)

            await websocket.send_text(json.dumps({
                "type": "transcript",
                "text": event.get("content", ""),
            }))

            from agents.orchestrator import get_compiled_graph
            graph = await get_compiled_graph()
            config = {"configurable": {"thread_id": case_id}}
            state = await graph.aget_state(config)
            if state and state.values:
                existing = state.values.get("channel_history", [])
                await graph.aupdate_state(config, {
                    "channel_history": existing + [event],
                    "_raw_events": [{"channel": "voice", "content": event["content"]}],
                })

    except WebSocketDisconnect:
        pass
