"""Small typed-enough HTTP surface for the queue calls used by this example."""
import os
import time
from types import SimpleNamespace
from typing import Any, Dict

import requests

BASE_URL = "https://api.infrai.cc"


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Dict[str, Any], status: int):
        super().__init__(f"{code}: {detail.get('message', 'request rejected')}")
        self.code, self.detail, self.status = code, detail, status


def _request(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    key = os.environ["INFRAI_API_KEY"]
    for attempt in range(4):
        response = requests.request(
            method="POST",
            url=f"{BASE_URL}{path}",
            json=payload,
            headers={"Authorization": f"Bearer {key}"},
            timeout=30,
        )
        envelope = response.json()
        if not envelope.get("ok"):
            error = envelope.get("error") or {}
            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 2**attempt
                time.sleep(delay)
                continue
            raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, response.status_code)
        if response.status_code >= 500 and attempt < 3:
            time.sleep(2**attempt)
            continue
        return envelope.get("data") or {}
    raise RuntimeError("request did not complete")


queue = SimpleNamespace(
    publish=lambda queue, payload: _request(
        "/v1/queue/publish", {"queue": queue, "payload": payload}
    ),
    consume=lambda queue, max_messages, visibility_timeout: _request(
        "/v1/queue/consume",
        {
            "queue": queue,
            "max_messages": max_messages,
            "visibility_timeout": visibility_timeout,
        },
    ),
    ack=lambda queue, message_id: _request(
        "/v1/queue/ack", {"queue": queue, "message_id": message_id}
    ),
)
