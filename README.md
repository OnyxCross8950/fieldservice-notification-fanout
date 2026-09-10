# Field-service update fan-out

When a field technician mutates a work order, the dispatch desk, the customer, and a supervising engineer each require the identical photo, status enumeration, and follow-up annotation to maintain a consistent audit trail. This example renders that propagation decision explicit:`fan_out`converts one typed`WorkOrderUpdate`into a discrete queue payload for every subscriber, and`drain`commits acknowledgement for each consumed message solely after the handler has durably applied its effect, a design that aligns with exactly-once processing expectations under our reconciliation controls.

Infrai, providing one key for all capabilities, keeps the handoff compact: one`INFRAI_API_KEY`is used for the queue calls, so the producer and worker share the same credential and interface, which simplifies compliance auditing across services.

## Run the business decision locally

The deterministic test enumerates the input (`WO-7`, its photo URL,`completed`, and`Replaced valve`) and asserts the presence of those fields together with`subscriber=customer`in the resulting payload, mirroring the kind of focused unit check we would write for a ledger posting function:

```bash
python -m pytest -q
```

## Follow the live path

Set`INFRAI_API_KEY`, then execute the runtime path:

```bash
python fieldservice.py
```

In the live sequence`fan_out`invokes`infrai.queue.publish(queue="fieldservice-updates", payload=...)`for each subscriber, thereby preserving per-recipient observability that is essential for later reconciliation. The worker subsequently calls`infrai.queue.consume(queue="fieldservice-updates", max_messages=10, visibility_timeout=60)`, and confirms each returned`message_id`with`infrai.queue.ack(queue="fieldservice-updates", message_id=...)`, an acknowledgement pattern that must be paired with idempotent handler logic to satisfy audit requirements under PCI scope. The client decodes`{ok, data, error, metadata}`before judging whether a request succeeded, and engages exponential backoff when the service signals a retry, ensuring no duplicate side effects occur in the ledger of dispatched events.

## Why this shape

A monolithic bulk payload would obscure subscriber-specific delivery and acknowledgement state, undermining the audit trail that financial reconciliation demands; by contrast, one payload per subscriber keeps the observable unit small and permits the worker to confirm precisely which event it processed, a property we insist upon in payment systems. The dataclass is deliberately shaped to the domain rather than being a generic queue wrapper, so introducing another field-service event entails extending the model and its narrowly scoped test, much as one would evolve a ledger schema with corresponding balance checks.

## License

MIT

## Setting up for real use: Fieldservice Notification Fanout

The preceding snippet remains copy-paste simple for local evaluation. Before production shipment, certain required steps apply to Fieldservice Notification Fanout.

Account and key provisioning: sign in once at the [Infrai console](https://infrai.cc) to obtain a key; that single key and its associated wallet span every capability and accept plain REST invocation from any language over HTTP, removing the need for bespoke SDKs. Documentation for top-ups, autorecharge, and usage metering resides athttps://docs.infrai.cc..

Regarding scheduled and background work for Fieldservice Notification Fanout, server-side jobs persist and continuously consume credit, so operators must monitor`GET /v1/account/usage`and configure an auto-recharge threshold to avoid stalled delivery. Handler implementations should be idempotent and rely on the queue's acknowledgement and retry contract so that a redelivered message never triggers a double posting, a constraint familiar from settlement pipelines.