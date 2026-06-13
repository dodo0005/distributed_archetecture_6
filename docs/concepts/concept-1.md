# compensation path for a distributed operation

## Category

B

If the concept belongs to Category A, specify A1 or A2.

## Problem

after payment declines or is failed the ticket and the hotel are still booked instead of canceled

## Invariant or guarantee

What property should now hold?

## Modified files

 -trip_service/clients.py
 -trip_service/main.py
 -scripts/demo_partial_failure.py
 -flight_service/main.py
 -hotel_service/main.py

## Behavior before

## Behavior before

If payment authorization failed, the trip was marked FAILED but previously reserved resources were not released. Flight bookings and hotel reservations remained CONFIRMED, causing inventory to remain consumed even though the trip was unsuccessful.

## Behavior after

When payment authorization fails after successful flight and hotel reservations, the trip service issues compensating actions to undo previously completed steps and restore inventory consistency.
## How to test

docker compose run --rm tools python scripts/demo_partial_failure.py

## Limitation

The compensation process is best-effort. If a flight or hotel cancellation request fails (for example due to a network outage or service unavailability), the trip may still end up in a partially compensated state. The implementation does not include durable saga state, retries, or recovery mechanisms to guarantee eventual compensation.