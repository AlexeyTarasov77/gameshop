import asyncio
from sse_starlette import EventSourceResponse
from core.api.schemas import MessageDTO


message_queue = asyncio.Queue()


async def send_message(msg: MessageDTO):
    await message_queue.put(msg)


async def message_queue_consumer():
    while True:
        msg = await message_queue.get()
        if not isinstance(msg, MessageDTO):
            raise TypeError(
                "Invalid message in queue: %s. Expected MessageDTO instance" % msg
            )
        yield msg.model_dump(mode="json")


async def message_stream():
    return EventSourceResponse(message_queue_consumer())
