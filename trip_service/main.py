import hashlib
import json
import logging
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI, Header, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from shared.logging import configure_logging
from trip_service import clients, db, events
from trip_service.pricing import calculate_amount_cents
from trip_service.schemas import CreateTripRequest

SERVICE_NAME = "trip-service"


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(SERVICE_NAME)
    await db.connect_with_retry()
    await db.init_db()
    yield
    await db.close()


app = FastAPI(title="Trip Service", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": SERVICE_NAME}


@app.post("/admin/reset")
async def reset() -> dict[str, str]:
    await db.reset_db()
    return {"status": "ok"}


@app.get("/debug/state")
async def debug_state() -> dict:
    return await db.state()

def hash_trip_request(request: CreateTripRequest) -> str:
    if hasattr(request, "model_dump"):
        data = request.model_dump(mode="json")
    else:
        data = request.dict()

    encoded = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@app.get("/trips")
async def list_trips() -> list[dict]:
    return (await db.state())["trips"]


@app.get("/trips/{trip_id}")
async def get_trip(trip_id: UUID) -> dict:
    trip = await db.get_trip(trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip


@app.post("/trips")
async def create_trip(
    request: CreateTripRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    if idempotency_key:
        request_hash = hash_trip_request(request)

        idempotency_state = await db.begin_idempotent_request(
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )

        if idempotency_state["action"] == "conflict":
            raise HTTPException(
                status_code=409,
                detail="This Idempotency-Key was already used with a different request body.",
            )

        if idempotency_state["action"] == "in_progress":
            raise HTTPException(
                status_code=409,
                detail="A request with this Idempotency-Key is already in progress.",
            )

        if idempotency_state["action"] == "replay":
            return JSONResponse(
                status_code=idempotency_state["response_status"],
                content=idempotency_state["response_body"],
                headers={"Idempotency-Replayed": "true"},
            )
    trip = await db.create_trip(
        user_id=request.user_id,
        traveler_name=request.traveler_name,
        flight_id=request.flight_id,
        hotel_id=request.hotel_id,
        nights=request.nights,
    )
    trip_id = trip["id"]

    try:
        # INTENTIONAL NAIVE DESIGN:
        # This is a plain sequence of remote calls. There is no saga state
        # machine, compensation, TCC, 2PC, retry policy, or idempotency key.
        flight_booking = await clients.book_flight(
            flight_id=request.flight_id,
            trip_id=str(trip_id),
            traveler_name=request.traveler_name,
            delay_after_check_ms=request.simulate.flight_delay_after_check_ms,
        )
        trip = await db.update_trip(trip_id, flight_booking_id=UUID(flight_booking["id"]))

        hotel_reservation = await clients.reserve_hotel(
            hotel_id=request.hotel_id,
            trip_id=str(trip_id),
            traveler_name=request.traveler_name,
            nights=request.nights,
            delay_after_check_ms=request.simulate.hotel_delay_after_check_ms,
            force_fail=request.simulate.hotel_force_fail,
        )
        trip = await db.update_trip(trip_id, hotel_reservation_id=UUID(hotel_reservation["id"]))

        flight = await clients.get_flight(request.flight_id)
        hotel = await clients.get_hotel(request.hotel_id)
        amount_cents = calculate_amount_cents(
            flight_price_cents=flight["price_cents"],
            hotel_price_per_night_cents=hotel["price_per_night_cents"],
            nights=request.nights,
        )
        trip = await db.update_trip(trip_id, amount_cents=amount_cents)

        payment = await clients.authorize_payment(
            trip_id=str(trip_id),
            amount_cents=amount_cents,
            force_decline=request.simulate.payment_force_decline,
            force_error=request.simulate.payment_force_error,
            delay_ms=request.simulate.payment_delay_ms,
        )
        trip = await db.update_trip(
            trip_id,
            payment_authorization_id=UUID(payment["id"]),
            status="CONFIRMED",
            error_message=None,
        )
    except Exception as exc:

        # compensate hotel
        if trip.get("hotel_reservation_id"):
            try:
                await clients.cancel_hotel_reservation(
                    str(trip["hotel_reservation_id"])
                )
            except Exception:
                logging.exception("Hotel compensation failed")

        # compensate flight
        if trip.get("flight_booking_id"):
            try:
                await clients.cancel_flight_booking(
                    str(trip["flight_booking_id"])
                )
            except Exception:
                logging.exception("Flight compensation failed")

        failed = await db.update_trip(
            trip_id,
            status="FAILED",
            error_message=str(exc),
        )

        error_body = {
            "detail": {
                "trip_id": str(trip_id),
                "error": failed["error_message"],
            }
        }

        if idempotency_key:
            await db.finish_idempotent_request(
                idempotency_key,
                status="FAILED",
                response_status=502,
                response_body=error_body,
            )

        raise HTTPException(
            status_code=502,
            detail={
                "trip_id": str(trip_id),
                "error": failed["error_message"],
            },
        )

    try:
        await events.publish_confirmation(trip, publish_twice=request.simulate.publish_event_twice)
    except Exception:
        logging.exception("Failed to publish trip.confirmed event")

    response_body = jsonable_encoder(trip)

    if idempotency_key:
        await db.finish_idempotent_request(
            idempotency_key,
            status="COMPLETED",
            response_status=200,
            response_body=response_body,
        )

    return response_body

