import asyncio
import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import require_auth
from app.db.models import User
from app.services.events import broadcaster

router = APIRouter(prefix="/api", tags=["events"])


async def _event_stream(user_id: int):
    queue = broadcaster.subscribe()
    try:
        while True:
            try:
                message = await asyncio.wait_for(queue.get(), timeout=15.0)
                if user_id not in message.get("user_ids", []):
                    continue
                payload = json.dumps({"type": message["type"], "data": message["data"]})
                yield f"data: {payload}\n\n"
            except asyncio.TimeoutError:
                yield ": heartbeat\n\n"
    finally:
        broadcaster.unsubscribe(queue)


@router.get("/events")
async def events_route(user: User = Depends(require_auth)) -> StreamingResponse:
    return StreamingResponse(_event_stream(user.id), media_type="text/event-stream")
