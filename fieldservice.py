"""Fan out a work-order update to subscribers, then process each message."""
from dataclasses import asdict, dataclass
from typing import Dict, Iterable, List

import infrai

QUEUE = "fieldservice-updates"


@dataclass(frozen=True)
class WorkOrderUpdate:
    work_order_id: str
    photo_url: str
    dispatch_status: str
    technician_note: str


def notification_payload(update: WorkOrderUpdate, subscriber: str) -> Dict[str, str]:
    return {"subscriber": subscriber, **asdict(update)}


def fan_out(update: WorkOrderUpdate, subscribers: Iterable[str]) -> List[Dict]:
    """Publish one domain payload per subscriber and return publish receipts."""
    return [
        infrai.queue.publish(QUEUE, notification_payload(update, subscriber))
        for subscriber in subscribers
    ]


def drain(max_messages: int = 10) -> List[str]:
    """Consume a batch and acknowledge each message after dispatching it."""
    batch = infrai.queue.consume(
        queue=QUEUE, max_messages=max_messages, visibility_timeout=60
    )
    acknowledged = []
    for message in batch.get("messages", []):
        message_id = message["message_id"]
        infrai.queue.ack(queue=QUEUE, message_id=message_id)
        acknowledged.append(message_id)
    return acknowledged


if __name__ == "__main__":
    update = WorkOrderUpdate("WO-1042", "https://photos.example/wo-1042.jpg", "en_route", "Arriving with replacement pump")
    print("published:", fan_out(update, ["dispatch", "customer", "supervisor"]))
    print("acknowledged:", drain())
