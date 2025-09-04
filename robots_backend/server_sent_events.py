from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse, JSONResponse
import asyncio
import json
from queue import Queue, Empty

router = APIRouter()

# Single global queue (simple case). If you need multiple concurrent searches,
# upgrade this to a dict of queues keyed by a stream_id.
url_queue: Queue[str] = Queue()
# Special completion marker
STREAM_COMPLETE = "__STREAM_COMPLETE__"

def add_url_to_stream(url: str):
    """Push a single URL immediately."""
    url_queue.put(url)

def signal_search_started():
    """Signal that the deep search has started."""
    url_queue.put("__SEARCH_STARTED__")

def signal_stream_complete():
    """Signal that the deep search has completed."""
    url_queue.put(STREAM_COMPLETE)

def clear_url_stream():
    """Empty the queue before a new deep_search starts."""
    try:
        while True:
            url_queue.get_nowait()
    except Empty:
        pass

async def url_stream_generator(request: Request):
    """
    Stream one SSE event per discovered URL, emitted as soon as it is queued.
    No busy-waiting/polling: we block on queue.get() in a thread pool.
    """
    # Send a tiny initial event so the browser renders the stream immediately.
    yield "event: keepalive\ndata: {}\n\n"

    loop = asyncio.get_running_loop()

    while True:
        # If client disconnected, stop.
        if await request.is_disconnected():
            break

        # Block until a new URL is available, off the event loop:
        url = await loop.run_in_executor(None, url_queue.get)
        
        # Check for special signals
        if url == "__SEARCH_STARTED__":
            # Send search started event
            yield f"data: {json.dumps({'started': True})}\n\n"
            continue
        elif url == STREAM_COMPLETE:
            # Send completion event and terminate stream
            yield f"data: {json.dumps({'complete': True})}\n\n"
            break
            
        # Stream a single URL per message:
        payload = json.dumps({"url": url})
        yield f"data: {payload}\n\n"

@router.get("/sse/urls")
async def stream_urls(request: Request):
    return StreamingResponse(
        url_stream_generator(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "false",
        },
    )

@router.options("/sse/urls")
async def options_sse_urls():
    return JSONResponse(
        content={"message": "OK"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "false",
        },
    )
