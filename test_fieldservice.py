from fieldservice import WorkOrderUpdate, notification_payload


def test_notification_keeps_photo_status_and_technician_follow_up():
    update = WorkOrderUpdate("WO-7", "https://photos.example/7.jpg", "completed", "Replaced valve")
    payload = notification_payload(update, "customer")
    assert payload == {
        "subscriber": "customer",
        "work_order_id": "WO-7",
        "photo_url": "https://photos.example/7.jpg",
        "dispatch_status": "completed",
        "technician_note": "Replaced valve",
    }
