"""Tiny in-memory store for generated hero images.

Keeps illustrations out of the article stream: the orchestrator stores the image
and streams only a short id; the frontend fetches it from ``/api/image/{id}``.
This avoids sending a large base64 payload inline, which was breaking the stream.
"""
import threading
import time
import uuid

_LOCK = threading.Lock()
_STORE: dict[str, tuple[float, str]] = {}
_MAX_ITEMS = 64


def put_image(data_url: str) -> str:
    """Store a ``data:image/...;base64,...`` URL and return a short id."""
    image_id = uuid.uuid4().hex
    with _LOCK:
        _STORE[image_id] = (time.time(), data_url)
        if len(_STORE) > _MAX_ITEMS:
            for key, _ in sorted(_STORE.items(), key=lambda kv: kv[1][0])[: len(_STORE) - _MAX_ITEMS]:
                _STORE.pop(key, None)
    return image_id


def get_image(image_id: str) -> str | None:
    with _LOCK:
        item = _STORE.get(image_id)
    return item[1] if item else None
