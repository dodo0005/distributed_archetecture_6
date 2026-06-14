# Idempotency Key

## Category

C — Communication, consistency, or scaling
idempotency key for a client request

## Problem

The baseline trip_service accepts duplicate client requests as separate new bookings. If the same POST /trips request is sent twice, the service creates two trips and repeats all distributed side effects: flight booking, hotel reservation, payment authorization, and notification publishing.

## Invariant or guarantee

For requests with an Idempotency-Key header, the same request must not execute the distributed booking workflow more than once. A repeated request with the same key and same body must return the original saved response. The same key cannot be reused for a different request body.

## Modified files

* trip_service/db.py
* trip_service/main.py
* tests/test_intentional_flaws.py

## Behavior before

Sending the same POST /trips request twice created two different trips. It also created duplicate side effects in other services: two flight bookings, two hotel reservations, and two payment authorizations.

## Behavior after

trip_service stores idempotency keys durably in PostgreSQL. When a new Idempotency-Key is received, the service stores the key, hashes the request body, processes the trip, and saves the final response.

If the same key and same request body are received again, trip_service returns the saved response instead of calling flight_service, hotel_service, and payment_service again.

If the same key is reused with a different request body, trip_service returns 409 Conflict.

## How to test

Run: docker compose run --rm tools pytest

The test test_duplicate_request_with_same_idempotency_key_is_idempotent sends the same trip request twice with the same Idempotency-Key and verifies that only one trip, one flight booking, one hotel reservation, and one payment authorization are created.

The test test_same_idempotency_key_with_different_body_is_rejected verifies that reusing the same Idempotency-Key with a different request body returns 409 Conflict.

## Limitation

This implementation protects duplicate client retries at the trip_service API boundary only. It does not make the remote flight_service, hotel_service, or payment_service endpoints independently idempotent. It also does not solve message publication reliability; that would require a transactional outbox or another messaging reliability mechanism.
