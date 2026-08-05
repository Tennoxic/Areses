import asyncio

from app.schemas.base import CamelModel


class NewArticleEvent(CamelModel):
    article_id: int
    source_id: int
    title: str


class EventBroadcaster:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)

    async def publish(self, event_type: str, data: dict, user_ids: list[int]) -> None:
        message = {"type": event_type, "data": data, "user_ids": user_ids}
        for queue in list(self._subscribers):
            await queue.put(message)


broadcaster = EventBroadcaster()
