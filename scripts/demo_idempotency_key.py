import httpx

from common import base_trip_payload, get_state, pretty, reset_all

TRIP_URL = "http://trip-service:8000"


def main() -> None:
    reset_all()

    payload = base_trip_payload()
    headers = {"Idempotency-Key": "exam-idempotency-demo-key-1"}

    first = httpx.post(
        f"{TRIP_URL}/trips",
        json=payload,
        headers=headers,
        timeout=10,
    )

    second = httpx.post(
        f"{TRIP_URL}/trips",
        json=payload,
        headers=headers,
        timeout=10,
    )

    print("Same client request submitted twice with the same Idempotency-Key.")
    print("The second request should reuse the stored response instead of creating side effects again.")

    print("\nFirst status:", first.status_code)
    print("First response:")
    print(pretty(first.json()))

    print("\nSecond status:", second.status_code)
    print("Second response:")
    print(pretty(second.json()))
    print("Second response replay header:", second.headers.get("Idempotency-Replayed"))

    print("\nState:")
    state = get_state()
    print(pretty(state))

    trips = state["trip-service"]["trips"]
    flight_bookings = state["flight-service"]["flight_bookings"]
    hotel_reservations = state["hotel-service"]["hotel_reservations"]
    payments = state["payment-service"]["payment_authorizations"]
    notifications = state["notification-api"]["notifications"]

    print("\nCounts:")
    print("Trips:", len(trips))
    print("Flight bookings:", len(flight_bookings))
    print("Hotel reservations:", len(hotel_reservations))
    print("Payments:", len(payments))
    print("Notifications:", len(notifications))

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert second.headers.get("Idempotency-Replayed") == "true"
    assert len(trips) == 1
    assert len(flight_bookings) == 1
    assert len(hotel_reservations) == 1
    assert len(payments) == 1
    assert len(notifications) == 1

    print("\nOK: idempotency key prevented duplicate trip creation and duplicate side effects.")


if __name__ == "__main__":
    main()