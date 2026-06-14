# Database Transaction

## Category
A — A1: Integrity and atomicity
database transaction

## Problem
The baseline booking operations in flight_service and hotel_service perform two writes as separate database calls: first decrement available inventory, then insert a booking record. A failure between these two steps leaves the database in partial, inconsistent state inventory decremented but no booking created.

## Invariant or guarantee
A booking record must never exist without a corresponding decrement in inventory count. Both writes must succeed together or neither must persist.

## Modified files
- flight_service/main.py
- hotel_service/main.py

## Behavior before
If a failure occurred between the UPDATE (decrement seats) and the INSERT (booking record), seats would be permanently lost with no booking to show for it. The data would be silently corrupted.

## Behavior after
Both writes execute inside a single database transaction using asyncpg's conn.transaction(). If any error occurs before COMMIT, the entire transaction rolls back. No partial state is ever saved.

## How to test
Run: python scripts/demo_atomicity.py
DEMO 1 shows a successful booking (both writes committed together)
and a failed booking (both writes rolled back, state unchanged).

## Limitation
This transaction protects local atomicity within one service's database only. It does not coordinate across services if the flight booking commits but the hotel reservation fails afterward, the flight seat is already consumed. That cross-service problem requires a saga (Category B).