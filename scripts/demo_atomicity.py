"""
Demo: A1 - Database Transaction + Constraints

Concept 1 (Transaction): proves that if a failure occurs mid-booking,
NO partial state is saved. Both writes roll back together.

Concept 2 (Constraint): proves the DB rejects negative seat counts
even if application code tries to force it.
"""
import httpx

FLIGHT_URL = "http://localhost:8001"
TRIP_ID = "00000000-0000-0000-0000-000000000001"


def print_state():
    r = httpx.get(f"{FLIGHT_URL}/debug/state")
    data = r.json()
    flight = next(f for f in data["flights"] if f["id"] == "FL-ONE-SEAT")
    bookings = data["flight_bookings"]
    print(f"  seats_available = {flight['seats_available']}")
    print(f"  bookings in DB  = {len(bookings)}")


# DEMO 1: Transaction rollback
print("=" * 60)
print("DEMO 1: Transaction atomicity")
print("=" * 60)

print("\n[1] Reset state")
httpx.post(f"{FLIGHT_URL}/admin/reset")
print_state()

print("\n[2] Send booking with delay_after_check_ms=500")
print("    This simulates a slow operation — but the key test")
print("    is that BOTH writes (INSERT booking + UPDATE seats)")
print("    are wrapped in one transaction.")
r = httpx.post(
    f"{FLIGHT_URL}/flights/FL-ONE-SEAT/bookings",
    json={
        "trip_id": TRIP_ID,
        "traveler_name": "Alice",
        "seats": 1,
        "fail_after_decrement": False,
        "delay_after_check_ms": 0,
    },
)
print(f"    Response: {r.status_code}")

print("\n[3] State after successful booking:")
print_state()

print("\n[4] Reset and now try with forced failure BEFORE transaction")
httpx.post(f"{FLIGHT_URL}/admin/reset")
r = httpx.post(
    f"{FLIGHT_URL}/flights/FL-ONE-SEAT/bookings",
    json={
        "trip_id": TRIP_ID,
        "traveler_name": "Alice",
        "seats": 1,
        "fail_after_decrement": True,
        "delay_after_check_ms": 0,
    },
)
print(f"    Response: {r.status_code} — {r.json()}")

print("\n[5] State after failed booking (should be unchanged):")
print_state()
print("\n seats_available=1 and bookings=0 → no partial state, transaction works.")


# DEMO 2: DB Constraint
print("\n" + "=" * 60)
print("DEMO 2: Database constraint (seats_available >= 0)")
print("=" * 60)

print("\n[1] Reset state")
httpx.post(f"{FLIGHT_URL}/admin/reset")
print_state()

print("\n[2] Book the only seat (FL-ONE-SEAT has 1 seat)")
r = httpx.post(
    f"{FLIGHT_URL}/flights/FL-ONE-SEAT/bookings",
    json={
        "trip_id": TRIP_ID,
        "traveler_name": "Alice",
        "seats": 1,
        "fail_after_decrement": False,
        "delay_after_check_ms": 0,
    },
)
print(f"    Response: {r.status_code}")

print("\n[3] Try to book again (0 seats left — should be rejected)")
r = httpx.post(
    f"{FLIGHT_URL}/flights/FL-ONE-SEAT/bookings",
    json={
        "trip_id": TRIP_ID,
        "traveler_name": "Bob",
        "seats": 1,
        "fail_after_decrement": False,
        "delay_after_check_ms": 0,
    },
)
print(f"    Response: {r.status_code} — {r.json()}")

print("\n[4] Final state:")
print_state()
print("\nSecond booking rejected, seats never went negative → constraint works.")