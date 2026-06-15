# Pessimistic Locking

## Category

A — A2: Concurrency control

## Problem

The baseline flight and hotel booking endpoints read available inventory outside of any database transaction, check it in application code, and then open a separate transaction to write. Under concurrent requests, two clients can both read the same inventory value, both pass the availability check, and both proceed to decrement causing overbooking. The existing CHECK constraint catches the second write and rolls it back, but the caller receives a raw database error instead of a clean rejection, and the race window remains.

## Invariant or guarantee

At most one booking for the last available seat or room must succeed when multiple requests arrive simultaneously. No request may observe a stale inventory count and proceed to book a resource that has already been taken.

## Modified files

- flight_service/main.py
- hotel_service/main.py

## Behavior before

Two concurrent requests to `POST /flights/FL-ONE-SEAT/bookings` could both read `seats_available = 1`, both pass the application check, and both attempt to decrement. The second decrement would violate the CHECK constraint and produce an unhandled database error. With the artificial `delay_after_check_ms` parameter, this race is reliably reproducible: 20 concurrent requests would produce multiple apparent successes or raw 500 errors rather than exactly one success and clean 409 rejections for the rest.

## Behavior after

The SELECT that reads inventory now uses `FOR UPDATE` on the same connection and inside the same transaction as the INSERT and UPDATE. Postgres acquires an exclusive row lock at read time. Concurrent requests for the same flight or hotel row queue behind the lock. When the first transaction commits and decrements inventory to zero, each subsequent request re-reads the updated row, sees zero seats or rooms, and returns a clean 409. No two bookings for the last available resource can succeed.

## How to test

```bash
docker compose run --rm tools python scripts/demo_overbooking.py
```

The script fires 20 concurrent requests for a flight with exactly one seat available, with a 200 ms artificial delay between the check and the write. After the fix, the script asserts:

- exactly 1 response with status 200
- all remaining responses with status 409
- `seats_available` is 0 in the final database state

The script prints `PASS` if all assertions hold and exits with a non-zero code if any fail.

## Limitation

The row lock serialises concurrent access to the same row. Under very high contention on a single resource, requests queue and latency increases proportionally to queue depth multiplied by lock-hold time. This is acceptable for an inventory system where contention on a single seat is inherently brief, but would not scale to a hotspot with thousands of simultaneous writers.

The lock protects inventory within one service's database only. It does not coordinate across services: a flight seat can be locked and decremented while the subsequent hotel reservation fails, leaving the flight consumed. That cross-service problem is addressed separately by the compensation concept (Category B).
