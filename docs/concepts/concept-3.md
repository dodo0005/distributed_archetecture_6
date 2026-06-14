# Database Constraints

## Category
A — A1: Integrity and atomicity

## Problem
The baseline application only checks seat/room availability in application code before writing. The database itself has no rule preventing inventory from going negative. A bug, a race condition, or a concurrent request could bypass the application-level check and write an invalid value directly to the database.

## Invariant or guarantee
seats_available must never be negative in the flights table.
rooms_available must never be negative in the hotels table.
This must be enforced at the database level, not just in Python.

## Modified files
- flight_service/db.py
- hotel_service/db.py

## Behavior before
No database-level protection existed. If application code had a bug or two concurrent requests slipped through the availability check simultaneously, the database would happily store a negative value.

## Behavior after
A CHECK constraint on the flights and hotels tables rejects any INSERT or UPDATE that would make inventory negative, regardless of what the application code does. The database is the last line of defense.

## How to test
Run: python scripts/demo_atomicity.py
DEMO 2 shows that after all seats are booked, a second booking attempt is rejected. The constraint prevents seats from going below 0.

## Limitation
Constraints enforce valid values but do not prevent race conditions between concurrent reads and writes. Two requests can both read seats_available=1, both pass the application check, and then one will be rejected by the constraint while the other succeeds. The constraint catches the violation but does not prevent the conflict that requires concurrency control (A2).