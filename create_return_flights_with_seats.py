# ...existing code...
"""
Create return-flight rows (swap source/destination) for existing flights and add seats
using the pattern you specified:

Business: 1A..1E, 2A..2E
Economy:  3A..3E, 4A..4E, 5A..5E

Usage (PowerShell):
  Set-Location 'd:\InfosysSpringboard'
  python .\scripts\create_return_flights_with_seats.py --offset-days 1
  python .\scripts\create_return_flights_with_seats.py --flight-ids 1,2 --offset-days 2

Options:
  --offset-days N       : number of days after original arrival to schedule return (default 1)
  --flight-ids id,id..  : optional comma-separated list of flight_ids to mirror (default: all)
"""
import argparse
import random
from datetime import timedelta
from FlightBookingSimulatorBackend import SessionLocal, Flight, Seat

SEAT_PATTERN = []
# Business rows 1..2 (A..E)
for r in (1, 2):
    for c in ("A", "B", "C", "D", "E"):
        SEAT_PATTERN.append((f"{r}{c}", "Business"))
# Economy rows 3..5 (A..E)
for r in (3, 4, 5):
    for c in ("A", "B", "C", "D", "E"):
        SEAT_PATTERN.append((f"{r}{c}", "Economy"))


def unique_flight_number(db, base):
    cand = base + "R"
    tries = 0
    while db.query(Flight).filter(Flight.flight_number == cand).first() and tries < 50:
        cand = f"{base}R{random.randint(10,99)}"
        tries += 1
    return cand


def run(offset_days: int = 1, flight_ids: list[int] | None = None):
    db = SessionLocal()
    created = []
    try:
        q = db.query(Flight)
        if flight_ids:
            q = q.filter(Flight.flight_id.in_(flight_ids))
        flights = q.all()
        if not flights:
            print("No flights found to mirror.")
            return

        for f in flights:
            # skip if a return leg already exists for same airline and swapped route
            existing = (
                db.query(Flight)
                .filter(
                    Flight.airline_id == f.airline_id,
                    Flight.source == f.destination,
                    Flight.destination == f.source
                )
                .first()
            )
            if existing:
                print(f"[skip] return already exists for flight {f.flight_id} -> {existing.flight_id}")
                continue

            duration = f.arrival_time - f.departure_time
            new_departure = f.arrival_time + timedelta(days=offset_days)
            new_arrival = new_departure + duration

            new_flight_no = unique_flight_number(db, f.flight_number)

            new_f = Flight(
                airline_id=f.airline_id,
                flight_number=new_flight_no,
                source=f.destination,
                destination=f.source,
                departure_time=new_departure,
                arrival_time=new_arrival,
                base_fare=f.base_fare
            )
            db.add(new_f)
            db.commit()  # commit to obtain new_f.flight_id
            db.refresh(new_f)

            # create seats per pattern (skip seats that already exist)
            existing_seats = set(s[0] for s in db.query(Seat.seat_number).filter(Seat.flight_id == new_f.flight_id).all())
            to_create = []
            for seat_number, seat_class in SEAT_PATTERN:
                if seat_number in existing_seats:
                    continue
                to_create.append(
                    Seat(flight_id=new_f.flight_id, seat_number=seat_number, seat_class=seat_class, is_booked=0)
                )
            if to_create:
                db.add_all(to_create)
                db.commit()
            created.append((new_f.flight_id, new_f.flight_number, len(to_create)))

            print(f"[created] flight_id={new_f.flight_id} flight_number={new_f.flight_number} seats_added={len(to_create)}")
    except Exception as e:
        db.rollback()
        print("Error:", e)
    finally:
        db.close()

    print(f"Done. Created {len(created)} return flights.")
    for fid, fno, seats in created:
        print(f" - {fid} / {fno} (+{seats} seats)")
# ...existing code...

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--offset-days", type=int, default=1, help="days after original arrival for return departure")
    parser.add_argument("--flight-ids", type=str, default=None, help="comma-separated flight ids to mirror (optional)")
    args = parser.parse_args()
    ids = None
    if args.flight_ids:
        ids = [int(x.strip()) for x in args.flight_ids.split(",") if x.strip().isdigit()]
    run(offset_days=args.offset_days, flight_ids=ids)