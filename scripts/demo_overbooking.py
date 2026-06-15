from __future__ import annotations

import asyncio
from uuid import uuid4

import httpx

from common import FLIGHT_URL, pretty, reset_all


async def try_book(client: httpx.AsyncClient) -> httpx.Response:
    return await client.post(
        f"{FLIGHT_URL}/flights/FL-ONE-SEAT/bookings",
        json={
            "trip_id": str(uuid4()),
            "traveler_name": "Race Condition Student",
            "seats": 1,
            "delay_after_check_ms": 200,
            "fail_after_decrement": False,
        },
    )


async def run_race() -> None:
    async with httpx.AsyncClient(timeout=30) as client:
        responses = await asyncio.gather(*[try_book(client) for _ in range(20)])
        state = (await client.get(f"{FLIGHT_URL}/debug/state")).json()

    successful = [r for r in responses if r.status_code == 200]
    rejected = [r for r in responses if r.status_code == 409]
    errors = [r for r in responses if r.status_code not in (200, 409)]
    one_seat = next(f for f in state["flights"] if f["id"] == "FL-ONE-SEAT")

    print(f"Successful bookings : {len(successful)}")
    print(f"Rejected (409)      : {len(rejected)}")
    print(f"Unexpected errors   : {len(errors)}")
    print(f"Final seats_available: {one_seat['seats_available']}")

    assert len(successful) == 1, f"FAIL: expected exactly 1 success, got {len(successful)}"
    assert one_seat["seats_available"] == 0, f"FAIL: seats should be 0, got {one_seat['seats_available']}"
    assert len(errors) == 0, f"FAIL: unexpected error responses: {[r.text for r in errors]}"

    print("\nPASS: pessimistic locking prevented overbooking.")
    print("Exactly 1 booking succeeded. All others received a clean 409.")
    print("\nFinal flight state:")
    print(pretty(state))


def main() -> None:
    reset_all()
    asyncio.run(run_race())


if __name__ == "__main__":
    main()

