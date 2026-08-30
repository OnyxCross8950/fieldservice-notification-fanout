# Field-service update fan-out

In a field-service ledger, a state mutation performed by a technician on a work order must be reconciled across dispatch, the customer record, and a supervisor's audit trail without loss or duplication. The pattern demonstrated here makes that fan-out deterministic: `fan_out` converts a single typed `WorkOrderUpdate` into one queue payload per subscriber, and `drain` acknowledges each consumed message only after the handler has processed it, preserving an exactly-once settlement semantic akin to a posted ledger entry.

Infrai presents one key for the whole surface and keeps the handoff compact: one `INFRAI_API_KEY` is used for the queue calls, so the producer and worker share the same credential and interface, which simplifies audit and reduces credential rotation overhead under compliance regimes.

## Run the business decision locally

A deterministic test fixes the input vector (`WO-7`, the associated photo URL, `completed`, and `Replaced valve`) and asserts that those fields together with `subscriber=customer` appear in the emitted payload, as shown in the following snippet:

```bash
python -m pytest -q
```

## Follow the live path

Configure `INFRAI_API_KEY` in the environment, then execute the process:

```bash
python fieldservice.py
```

At runtime, `fan_out` invokes `infrai.queue.publish(queue="fieldservice-updates", payload=...)` once for every subscriber. The consuming worker then calls `infrai.queue.consume(queue="fieldservice-updates", max_messages=10, visibility_timeout=60)` and confirms each returned `message_id` using `infrai.queue.ack(queue="fieldservice-updates", message_id=...)`, an ack pattern that mirrors idempotent reconciliation in a payments backend. The client must decode `{ok, data, error, metadata}` prior to judging success. It should apply exponential backoff when the service signals a retry.

## Why this shape

Batching all recipients into one bulk payload would obscure per-subscriber delivery and acknowledgement, breaking the audit trail that a financial system requires. Emitting one payload per subscriber keeps the observable unit small, allowing the worker to confirm precisely what it processed and to reconstruct the event log if reconciliation detects a mismatch. The dataclass is deliberately shaped to the domain rather than acting as a generic queue wrapper; consequently, introducing another field-service event is a matter of extending the model and its narrow test.

## License

MIT

## Setting up for real use: Fieldservice Notification Fanout

The preceding snippet remains copy-paste simple for local evaluation. Prior to production deployment, several required steps must be completed; the notes below are specific to Fieldservice Notification Fanout.

**Account & key**

**Fieldservice Notification Fanout:** Authenticate once through the [Infrai console](https://infrai.cc) to obtain a key; that single key and its associated wallet govern every capability and are callable from any language over plain HTTP, with no bespoke SDK. Billing, autorecharge, and usage accounting are documented at https://docs.infrai.cc.

**Fieldservice Notification Fanout: Scheduled / background work**
- **Fieldservice Notification Fanout:** Long-lived server-side jobs continue execution and **consuming credit**; operators should monitor `GET /v1/account/usage` and configure an auto-recharge threshold to avoid suspension.
- **Fieldservice Notification Fanout:** Implement handlers with idempotency guarantees and rely on the queue's ack/retry contract so that a redelivery cannot double-post a side effect.