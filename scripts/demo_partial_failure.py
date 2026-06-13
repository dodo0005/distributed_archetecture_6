from common import base_trip_payload, create_trip, get_state, pretty, reset_all


def main() -> None:
    reset_all()
    response = create_trip(base_trip_payload(payment_force_decline=True))

    print("Payment failed after flight and hotel succeeded.")
    print("Compensation logic cancelled the flight booking.")
    print("Compensation logic cancelled the hotel reservation.")
    print("Inventory was restored and the trip was marked FAILED.")
    print("Trip response:")
    print(pretty(response.json()))
    print("State:")
    print(pretty(get_state()))


if __name__ == "__main__":
    main()

