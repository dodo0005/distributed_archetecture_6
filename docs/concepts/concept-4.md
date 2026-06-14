# Idempotency key for client trip request

## Category

C - Communication, consistency, or scaling.

## Problem

The baseline trip service creates a new trip every time the client sends POST /trips.

If the client retries the same request, the system can create duplicate trips, flight bookings, hotel reservations, payments, and notifications.

## Invariant or guarantee

If the client sends the same request with the same Idempotency-Key, the trip service returns the stored response instead of running the booking workflow again.

The same key cannot be reused with a different request body.

## Modified files

trip_service/db.py
trip_service/main.py
scripts/demo_idempotency_key.py

## Behavior before

Sending the same trip request twice created two different trips and repeated the side effects in the other services.

## Behavior after

The first request stores the idempotency key, request hash, and response in the trip database.

A repeated request with the same key and same body returns the original response.

No second trip, flight booking, hotel reservation, payment, or notification is created.

## How to test

Run:

docker compose run --rm tools python scripts/demo_idempotency_key.py

The expected result is that both responses are the same and the final state contains only one trip and one set of side effects.

## Limitation

This only works when the client sends an Idempotency-Key.

It does not make the flight, hotel, or payment services independently idempotent.

If a request crashes while marked IN_PROGRESS, manual cleanup or timeout handling may be needed.
```