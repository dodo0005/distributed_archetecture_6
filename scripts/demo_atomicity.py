"""
Demo: A1 - Database Transaction + Constraint

Proves that if a failure occurs mid-booking, NO partial state is saved.
The transaction rolls back both writes together.
"""
import httpx

FLIGHT_URL = "http://localhost:8001"
TRIP_ID = "00000000-0000-0000-0000-000000000001"


def print_state():
    r = httpx.get(f"{FLIGHT_URL}/debug/state")
    data = r.json()
    flight = data["flights"][0]
    bookings = data["flight_bookings"]
    print(f"  seats_available = {flight['seats_available']}")
    print(f"  bookings in DB  = {len(bookings)}")


print("=== RESET ===")
httpx.post(f"{FLIGHT_URL}/admin/reset")
print_state()

print("\n=== Booking with forced failure mid-operation ===")
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
print(f"  Response: {r.status_code} — {r.json()}")

print("\n=== State after failed booking ===")
print_state()
print("\n If seats_available=1 and bookings=0, transaction rolled back correctly.")
print("If seats_available=0 and bookings=0, partial state — bug not fixed.")