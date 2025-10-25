"""
 - FlightBookingSimulator.py 

Key features implemented here:
- Connects to your existing MySQL DB 'FlightBooking' (uses schema you provided + small migrations)
- Booking flow where booking is created as 'Pending' and seat is reserved;
  payment endpoint confirms booking, generates PNR, and stores it in DB
- Dynamic pricing engine and background market simulator
- All important endpoints protected
"""

from typing import List, Optional, Dict, Annotated
from datetime import datetime, timedelta
import random
import string
import asyncio

from fastapi import FastAPI, HTTPException, Query, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, constr
from passlib.context import CryptContext
from contextlib import asynccontextmanager

from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, DECIMAL, ForeignKey, func
)
from sqlalchemy.orm import sessionmaker, DeclarativeBase, mapped_column, relationship, Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import URL

# ---------------------------
# DB CONNECTION (MySQL)
# ---------------------------
DB_USER = "root"
DB_PASSWORD = "Sandy@2004"  # placeholder; replace locally
DB_HOST = "localhost"
DB_PORT = 3306
DB_NAME = "FlightBooking"

DATABASE_URL = URL.create(
"mysql+pymysql",
username="root",
password="Sandy@2004",
host="localhost",
port=3306,
database="FlightBooking"
)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# ---------------------------
# SQLAlchemy base & models
# ---------------------------
class Base(DeclarativeBase):
    pass


class Airline(Base):
    __tablename__ = "Airlines"
    airline_id = mapped_column("airline_id", Integer, primary_key=True)
    airline_name = mapped_column("airline_name", String(255))
    iata_code = mapped_column("iata_code", String(2))
    flights = relationship("Flight", back_populates="airline", lazy="selectin")


class Flight(Base):
    __tablename__ = "Flights"
    flight_id = mapped_column("flight_id", Integer, primary_key=True)
    airline_id = mapped_column("airline_id", Integer, ForeignKey("Airlines.airline_id"), nullable=False)
    flight_number = mapped_column("flight_number", String(6))
    source = mapped_column("source", String(50))
    destination = mapped_column("destination", String(50))
    departure_time = mapped_column("departure_time", DateTime)
    arrival_time = mapped_column("arrival_time", DateTime)
    base_fare = mapped_column("base_fare", DECIMAL(10, 2))
    airline = relationship("Airline", back_populates="flights", lazy="joined")
    seats = relationship("Seat", back_populates="flight", lazy="selectin")
    bookings = relationship("Booking", back_populates="flight", lazy="selectin")


class Seat(Base):
    __tablename__ = "Seats"
    seat_id = mapped_column("seat_id", Integer, primary_key=True)
    flight_id = mapped_column("flight_id", Integer, ForeignKey("Flights.flight_id"), nullable=False)
    seat_number = mapped_column("seat_number", String(10))
    seat_class = mapped_column("seat_class", String(20))
    is_booked = mapped_column("is_booked", Integer)  # 0/1
    flight = relationship("Flight", back_populates="seats")


class Passenger(Base):
    __tablename__ = "Passengers"
    passenger_id = mapped_column("passenger_id", Integer, primary_key=True)
    full_name = mapped_column("full_name", String(100))
    email = mapped_column("email", String(50))
    phone = mapped_column("phone", String(13))
    bookings = relationship("Booking", back_populates="passenger", lazy="selectin")


class Booking(Base):
    __tablename__ = "Bookings"
    booking_id = mapped_column("booking_id", Integer, primary_key=True)
    passenger_id = mapped_column("passenger_id", Integer, ForeignKey("Passengers.passenger_id"), nullable=False)
    flight_id = mapped_column("flight_id", Integer, ForeignKey("Flights.flight_id"), nullable=False)
    seat_id = mapped_column("seat_id", Integer, ForeignKey("Seats.seat_id"), nullable=False)
    booking_date = mapped_column("booking_date", DateTime)
    amount_paid = mapped_column("amount_paid", DECIMAL(10,4))
    status = mapped_column("status", String(20))  
    pnr = mapped_column("pnr", String(12), nullable=True, unique = True)  
    passenger = relationship("Passenger", back_populates="bookings")
    flight = relationship("Flight", back_populates="bookings")


# ---------------------------
# FastAPI app & configs
# ---------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables and start background task
    Base.metadata.create_all(bind=engine)
    print("Tables created (if not existing)")
    asyncio.create_task(market_simulator(20))
    print("Market simulator started")
    yield  # FastAPI runs here
    # Shutdown code (optional)
    print("Application shutdown")

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Flight Booking Simulator with Dynamic Pricing",lifespan= lifespan)


origins = [
    "http://localhost:5500",
    "http://127.0.0.1:5500"
]


app.add_middleware(
    CORSMiddleware,
    allow_origins = origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# DB dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------
# Pydantic schemas
# ---------------------------
class RegisterIn(BaseModel):
    full_name: str
    email: str
    phone: Annotated[str,constr(min_length=10, max_length=10)]
    password: Annotated[str, constr(min_length=6)]


class LoginOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PassengerOut(BaseModel):
    passenger_id: int
    full_name: str
    email: str
    phone: str

class FlightSearchResult(BaseModel):
    flight_id: int
    flight_number: str
    airline: str
    origin: str
    destination: str
    departure_time: datetime
    arrival_time: datetime
    base_fare: float
    dynamic_price: float
    seats_available: int
    total_seats: int

class BookingCreateReq(BaseModel):
    flight_id: int
    seat_number: Optional[str] = None
    passenger_id: int  # preferred seat


class BookingPayReq(BaseModel):
    # simulate payment with minimal info
    payment_method: Optional[str] = "card"
    passenger_id : int

class BookingResponse(BaseModel):
    booking_id: int
    pnr: Optional[str]
    flight_number: str
    passenger_name: str
    seat_number: str
    amount_paid: float
    status: str
    booking_date: datetime


                                #-------------------------------------
                                # MILESTONE 1: CORE FLIGHT SEARCH DATA
                                #-------------------------------------

# ---------------------------
# Flight search endpoints (public)
# ---------------------------


@app.get("/flights", response_model=List[FlightSearchResult])
def list_flights(origin: Optional[str] = Query(None, alias="from"),
                 destination: Optional[str] = Query(None, alias="to"),
                 date: Optional[str] = None,
                 max_price: Optional[float] = None,
                 sort_by: Optional[str] = None,
                 db: Session = Depends(get_db)):
    q = db.query(Flight).join(Airline)
    if origin:
        q = q.filter(Flight.source.ilike(f"%{origin}%"))
    if destination:
        q = q.filter(Flight.destination.ilike(f"%{destination}%"))
    if date:
        try:
            d = datetime.fromisoformat(date)
        except Exception:
            raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
        q = q.filter(Flight.departure_time >= d, Flight.departure_time < d + timedelta(days=1))
    flights = q.all()
    out = []
    for f in flights:
        counts = _count_seats(db, f.flight_id)
        demand_index = 1.0 + (counts["booked"] / max(counts["total"], 1)) * 0.5
        dyn = _compute_dynamic_price(f.base_fare, seats_available=counts["available"], total_seats=counts["total"],
                                     departure_dt=f.departure_time, demand_index=demand_index)
        if max_price is not None and dyn > max_price:
            continue
        out.append(FlightSearchResult(
            flight_id=f.flight_id,
            flight_number=f.flight_number,
            airline=f.airline.airline_name if f.airline else "Unknown",
            origin=f.source,
            destination=f.destination,
            departure_time=f.departure_time,
            arrival_time=f.arrival_time,
            base_fare=float(f.base_fare),
            dynamic_price=dyn,
            seats_available=counts["available"],
            total_seats=counts["total"]
        ))
    if sort_by == "price":
        out.sort(key=lambda x: x.dynamic_price)
    elif sort_by == "duration":
        out.sort(key=lambda x: (x.arrival_time - x.departure_time).total_seconds())
    return out


@app.get("/flights/{flight_id}", response_model=FlightSearchResult)
def flight_detail(flight_id: int, db: Session = Depends(get_db)):
    f = db.query(Flight).filter(Flight.flight_id == flight_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Flight not found")
    counts = _count_seats(db, flight_id)
    demand_index = 1.0 + (counts["booked"] / max(counts["total"], 1)) * 0.5
    dyn = _compute_dynamic_price(f.base_fare, seats_available=counts["available"], total_seats=counts["total"],
                                 departure_dt=f.departure_time, demand_index=demand_index)
    return FlightSearchResult(
        flight_id=f.flight_id,
        flight_number=f.flight_number,
        airline=f.airline.airline_name if f.airline else "Unknown",
        origin=f.source,
        destination=f.destination,
        departure_time=f.departure_time,
        arrival_time=f.arrival_time,
        base_fare=float(f.base_fare),
        dynamic_price=dyn,
        seats_available=counts["available"],
        total_seats=counts["total"]
    )

                        #--------------------------------------------
                        #      MILESTONE 2: DYNAMIC PRICING ENGINE
                        #--------------------------------------------
# ---------------------------
# Utility functions (pricing & seat counts)
# ---------------------------
def _count_seats(db: Session, flight_id: int) -> Dict[str, int]:
    total = db.query(func.count(Seat.seat_id)).filter(Seat.flight_id == flight_id).scalar() or 0
    booked = db.query(func.count(Seat.seat_id)).filter(Seat.flight_id == flight_id, Seat.is_booked == 1).scalar() or 0
    available = total - booked
    return {"total": total, "booked": booked, "available": available}

def _compute_dynamic_price(base_fare_dec, seats_available: int, total_seats: int,
                           departure_dt: datetime, demand_index: float = 1.0) -> float:
    base_fare = float(base_fare_dec)
    seats_booked = max(total_seats - seats_available, 0)
    seat_ratio = seats_booked / max(total_seats, 1)
    seat_factor = 0.25 * (seat_ratio ** 2) + 0.12 * seat_ratio

    now = datetime.utcnow()
    days_to_depart = max((departure_dt - now).total_seconds() / 86400, 0.0)
    if days_to_depart < 1:
        time_factor = 0.6
    elif days_to_depart < 7:
        time_factor = 0.25
    elif days_to_depart < 30:
        time_factor = 0.08
    else:
        time_factor = -0.05

    demand_factor = (demand_index - 1.0) * 0.6
    jitter = random.uniform(-0.02, 0.03)

    multiplier = 1 + seat_factor + time_factor + demand_factor + jitter
    price = max(base_fare * multiplier, 0.5 * base_fare)
    return round(price, 2)

# ---------------------------
# Dynamic pricing endpoints (public)
# ---------------------------
@app.get("/dynamic_price/{flight_id}")
def dynamic_price(flight_id: int, db: Session = Depends(get_db)):
    f = db.query(Flight).filter(Flight.flight_id == flight_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Flight not found")
    counts = _count_seats(db, flight_id)
    demand_index = 1.0 + (counts["booked"] / max(counts["total"], 1)) * 0.5
    price = _compute_dynamic_price(f.base_fare, seats_available=counts["available"], total_seats=counts["total"],
                                   departure_dt=f.departure_time, demand_index=demand_index)
    return {
        "flight_id": flight_id,
        "flight_number": f.flight_number,
        "origin": f.source,
        "destination": f.destination,
        "departure_time": f.departure_time,
        "base_fare": float(f.base_fare),
        "dynamic_price": price,
        "seats_available": counts["available"],
        "total_seats": counts["total"]
    }


@app.get("/dynamic_price/all")
def dynamic_price_all(db: Session = Depends(get_db)):
    flights = db.query(Flight).all()
    out = []
    for f in flights:
        counts = _count_seats(db, f.flight_id)
        demand_index = 1.0 + (counts["booked"] / max(counts["total"], 1)) * 0.5
        price = _compute_dynamic_price(f.base_fare, seats_available=counts["available"], total_seats=counts["total"],
                                       departure_dt=f.departure_time, demand_index=demand_index)
        out.append({
            "flight_id": f.flight_id,
            "flight_number": f.flight_number,
            "origin": f.source,
            "destination": f.destination,
            "dynamic_price": price,
            "seats_available": counts["available"],
            "total_seats": counts["total"]
        })
    return {"count": len(out), "flights": out}


# ---------------------------
# Background market simulator
# ---------------------------

async def market_simulator(interval_seconds: int = 20):
    print("Market simulator started")
    while True:
        # run blocking DB operations in a thread so the event loop is not blocked
        def _sync_simulator_step():
            db = SessionLocal()
            try:
                flights = db.query(Flight.flight_id).all()
                if not flights:
                    db.close()
                    return
                sample = random.sample([f.flight_id for f in flights], k=min(3, len(flights)))
                for fid in sample:
                    # small chance to toggle seats to simulate bookings/cancellations
                    if random.random() < 0.25:
                        counts = _count_seats(db, fid)
                        # if available, randomly book one seat (simulate external booking)
                        if counts["available"] > 0 and random.random() < 0.6:
                            seat = db.query(Seat).filter(Seat.flight_id == fid, Seat.is_booked == 0).first()
                            if seat:
                                seat.is_booked = 1
                                db.add(seat)
                        else:
                            seat = db.query(Seat).filter(Seat.flight_id == fid, Seat.is_booked == 1).first()
                            if seat and random.random() < 0.5:
                                seat.is_booked = 0
                                db.add(seat)
                        db.commit()
            except Exception as e:
                db.rollback()
                print("Simulator error:", e)
            finally:
                db.close()

        await asyncio.to_thread(_sync_simulator_step)
        await asyncio.sleep(interval_seconds)


                    #-------------------------------------------------------
                    # MILESTONE 3: BOOKING WORKFLOW & TRANSACTION MANAGEMENT
                    #-------------------------------------------------------
# ---------------------------
# Booking workflow (protected)
#  - create booking -> status 'Pending' and seat reserved (is_booked=1)
#  - pay booking -> on success: status 'Confirmed', generate PNR and persist to DB
# ---------------------------


# Helper: generate PNR
def generate_pnr(length: int = 8) -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choice(chars) for _ in range(length))

@app.post("/bookings", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(req: BookingCreateReq, db: Session = Depends(get_db)):
    """
    Create a booking:
      - find flight, check seat availability
      - reserve a seat (mark is_booked=1) and insert Booking with status 'Pending' and pnr=NULL
      - return booking details (PNR generated only after payment)
    """
    passenger_id = req.passenger_id  # passenger_id sent in payload

    passenger = db.query(Passenger).filter(Passenger.passenger_id == passenger_id).first()
    if not passenger:
        raise HTTPException(status_code=404, detail="Passenger not found")
    
    pre_in_tx = db.in_transaction()
    # choose transaction context depending on whether a transaction already exists
    tx_ctx = db.begin_nested() if db.in_transaction() else db.begin()
    # start transaction
    try:
        with tx_ctx:
            flight = db.query(Flight).filter(Flight.flight_id == req.flight_id).first()
            if not flight:
                raise HTTPException(status_code=404, detail="Flight not found")
            
            counts = _count_seats(db, flight.flight_id)
            if counts["available"] <= 0:
                raise HTTPException(status_code=400, detail="No seats available")

            # pick seat: preferred or first available
           
            if req.seat_number:
                seat_row = (
                    db.query(Seat)
                    .filter(Seat.flight_id == flight.flight_id, Seat.seat_number == req.seat_number)
                    .with_for_update()
                    .first()
                )
                if not seat_row:
                    raise HTTPException(status_code=404, detail="Requested seat not found")
                if seat_row.is_booked == 1:
                    raise HTTPException(status_code=400, detail="Requested seat already booked")
            else:
                seat_row = (
                    db.query(Seat)
                    .filter(Seat.flight_id == flight.flight_id, Seat.is_booked == 0)
                    .with_for_update()
                    .first()
                )
                if not seat_row:
                    raise HTTPException(status_code=400, detail="No available seats (race)")

            # reserve seat immediately
            seat_row.is_booked = 1
            db.add(seat_row)
            db.flush()  # ensure seat update applied

            # recompute counts after reserve
            counts_after = _count_seats(db, flight.flight_id)
            demand_index = 1.0 + (counts_after["booked"] / max(counts_after["total"], 1)) * 0.5
            amount = _compute_dynamic_price(
                flight.base_fare,
                seats_available=counts_after["available"],
                total_seats=counts_after["total"],
                departure_dt=flight.departure_time,
                demand_index=demand_index
            )

            booking = Booking(
                passenger_id=passenger_id,
                flight_id=flight.flight_id,
                seat_id=seat_row.seat_id,
                booking_date=datetime.utcnow(),
                amount_paid=amount,
                status="Pending",
                pnr=None
            )
            db.add(booking)
            db.flush()
            db.refresh(booking)

       
            passenger_name = db.query(Passenger.full_name).filter(Passenger.passenger_id == passenger_id).scalar()
            response = BookingResponse(
                booking_id=booking.booking_id,
                pnr=None,
                flight_number=flight.flight_number,
                passenger_name=passenger_name or "",
                seat_number=seat_row.seat_number,
                amount_paid=float(booking.amount_paid),
                status=booking.status,
                booking_date=booking.booking_date or datetime.utcnow()
            )
        
        if pre_in_tx:
            db.commit()
        
        return response
    except HTTPException:
        raise
    except Exception as e:
         # the context managers will rollback on exception; surface a clear message
        try:
            db.rollback()
        except Exception:
                pass    
        raise HTTPException(status_code=500, detail=f"Booking creation failed: {e}")


class RoundtripCreateReq(BaseModel):
    outbound_flight_id: int
    outbound_seat_number: Optional[str] = None
    return_flight_id: int
    return_seat_number: Optional[str] = None
    passenger_id: int

@app.post("/bookings/roundtrip", response_model=List[BookingResponse], status_code=status.HTTP_201_CREATED)
def create_roundtrip(req: RoundtripCreateReq, db: Session = Depends(get_db)):
    """
    Create a roundtrip booking (two Booking rows: outbound + return) in a single transaction.
    Seats for both legs are reserved (is_booked=1) and bookings created with status 'Pending'.
    Returns a list with two BookingResponse objects (outbound, return).

    Validations:
      - passenger must exist
      - return flight must depart at least 1 hour after outbound arrival
      - both legs reserved/created in one transaction (atomic)
    """
    passenger_id = req.passenger_id
    passenger = db.query(Passenger).filter(Passenger.passenger_id == passenger_id).first()
    if not passenger:
        raise HTTPException(status_code=404, detail="Passenger not found")

    pre_in_tx = db.in_transaction()
    tx_ctx = db.begin_nested() if pre_in_tx else db.begin()

    created: List[BookingResponse] = []
    try:
        outbound_arrival: Optional[datetime] = None

        with tx_ctx:
            for idx, (flight_id, seat_number) in enumerate((
                (req.outbound_flight_id, req.outbound_seat_number),
                (req.return_flight_id, req.return_seat_number),
            )):
                flight = db.query(Flight).filter(Flight.flight_id == flight_id).first()
                if not flight:
                    raise HTTPException(status_code=404, detail=f"Flight {flight_id} not found")

                # for return leg ensure timing after outbound arrival (+1 hour buffer)
                if idx == 1 and outbound_arrival is not None:
                    if flight.departure_time <= outbound_arrival + timedelta(hours=1):
                        raise HTTPException(status_code=400, detail="Return flight must depart at least 1 hour after outbound arrival")

                counts = _count_seats(db, flight_id)
                if counts["available"] <= 0:
                    raise HTTPException(status_code=400, detail=f"No seats available for flight {flight_id}")

                if seat_number:
                    seat_row = (
                        db.query(Seat)
                        .filter(Seat.flight_id == flight_id, Seat.seat_number == seat_number)
                        .with_for_update()
                        .first()
                    )
                    if not seat_row:
                        raise HTTPException(status_code=404, detail=f"Requested seat {seat_number} not found on flight {flight_id}")
                    if seat_row.is_booked == 1:
                        raise HTTPException(status_code=400, detail=f"Requested seat {seat_number} already booked on flight {flight_id}")
                else:
                    seat_row = (
                        db.query(Seat)
                        .filter(Seat.flight_id == flight_id, Seat.is_booked == 0)
                        .with_for_update()
                        .first()
                    )
                    if not seat_row:
                        raise HTTPException(status_code=400, detail=f"No available seats (race) on flight {flight_id}")

                # reserve seat
                seat_row.is_booked = 1
                db.add(seat_row)
                db.flush()

                counts_after = _count_seats(db, flight_id)
                demand_index = 1.0 + (counts_after["booked"] / max(counts_after["total"], 1)) * 0.5
                amount = _compute_dynamic_price(
                    flight.base_fare,
                    seats_available=counts_after["available"],
                    total_seats=counts_after["total"],
                    departure_dt=flight.departure_time,
                    demand_index=demand_index
                )

                booking = Booking(
                    passenger_id=passenger_id,
                    flight_id=flight_id,
                    seat_id=seat_row.seat_id,
                    booking_date=datetime.utcnow(),
                    amount_paid=amount,
                    status="Pending",
                    pnr=None
                )
                db.add(booking)
                db.flush()
                db.refresh(booking)

                passenger_name = db.query(Passenger.full_name).filter(Passenger.passenger_id == passenger_id).scalar()
                created.append(BookingResponse(
                    booking_id=booking.booking_id,
                    pnr=None,
                    flight_number=flight.flight_number,
                    passenger_name=passenger_name or "",
                    seat_number=seat_row.seat_number,
                    amount_paid=float(booking.amount_paid),
                    status=booking.status,
                    booking_date=booking.booking_date or datetime.utcnow()
                ))

                # store outbound arrival time after processing first leg
                if idx == 0:
                    outbound_arrival = flight.arrival_time

        # commit if we used a nested (outer) transaction
        if pre_in_tx:
            db.commit()

        return created
    except HTTPException:
        raise
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Roundtrip booking failed: {e}")



@app.post("/bookings/pay/{booking_id}", response_model=BookingResponse)
def pay_booking(booking_id: int, payload: BookingPayReq, db: Session = Depends(get_db)):
    """
    Simulate payment:
      - passenger_id must be provided in payload
      - simulate success/failure
      - on success: generate PNR, set status 'Confirmed', persist PNR
      - on failure: leave booking as 'Pending', return failure message
    """
    passenger_id = payload.passenger_id  # passenger_id from payload

    try:
        with db.begin():
            booking = db.query(Booking).filter(Booking.booking_id == booking_id).with_for_update().first()
            if not booking:
                raise HTTPException(status_code=404, detail="Booking not found")
            if booking.passenger_id != passenger_id:
                raise HTTPException(status_code=403, detail="Not authorized for this booking")
            if booking.status == "Confirmed":
                # already paid
                flight_number = db.query(Flight.flight_number).filter(Flight.flight_id == booking.flight_id).scalar()
                seat_number = db.query(Seat.seat_number).filter(Seat.seat_id == booking.seat_id).scalar()
                passenger_name = db.query(Passenger.full_name).filter(Passenger.passenger_id == passenger_id).scalar()
                return BookingResponse(
                    booking_id=booking.booking_id,
                    pnr=booking.pnr,
                    flight_number=flight_number or "",
                    passenger_name=passenger_name or "",
                    seat_number=seat_number or "",
                    amount_paid=float(booking.amount_paid),
                    status=booking.status,
                    booking_date=booking.booking_date or datetime.utcnow()
                )

            # simulate payment outcome (70% chance success)
            success = random.random() < 0.7
            if success:
                booking.status = "Confirmed"
                # generate unique PNR
                pnr = generate_pnr()
                attempts = 0
                while db.query(Booking).filter(Booking.pnr == pnr).first() and attempts < 5:
                    pnr = generate_pnr()
                    attempts += 1
                booking.pnr = pnr
                db.add(booking)
                db.flush()

                flight_number = db.query(Flight.flight_number).filter(Flight.flight_id == booking.flight_id).scalar()
                seat_number = db.query(Seat.seat_number).filter(Seat.seat_id == booking.seat_id).scalar()
                passenger_name = db.query(Passenger.full_name).filter(Passenger.passenger_id == passenger_id).scalar()
                return BookingResponse(
                    booking_id=booking.booking_id,
                    pnr=booking.pnr,
                    flight_number=flight_number or "",
                    passenger_name=passenger_name or "",
                    seat_number=seat_number or "",
                    amount_paid=float(booking.amount_paid),
                    status=booking.status,
                    booking_date=booking.booking_date or datetime.utcnow()
                )
            else:
                # payment failed
                booking.status = "PaymentFailed"
                db.add(booking)
                db.flush()
                raise HTTPException(status_code=402, detail="Payment failed (simulated). Try again.")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Payment processing failed: {e}")

@app.get("/bookings/passenger/{passenger_id}")
def get_my_bookings(passenger_id: int, db: Session = Depends(get_db)):
    bookings = db.query(Booking).filter(Booking.passenger_id == passenger_id,
                                        Booking.status != "Cancelled").all()
    out = []
    for b in bookings:
        flight_number = db.query(Flight.flight_number).filter(Flight.flight_id == b.flight_id).scalar()
        seat_number = db.query(Seat.seat_number).filter(Seat.seat_id == b.seat_id).scalar()
        passenger_name = db.query(Passenger.full_name).filter(Passenger.passenger_id == b.passenger_id).scalar()
        out.append(BookingResponse(
            booking_id=b.booking_id,
            pnr=b.pnr,
            flight_number=flight_number or "",
            passenger_name=passenger_name or "",
            seat_number=seat_number or "",
            amount_paid=float(b.amount_paid),
            status=b.status,
            booking_date=b.booking_date or datetime.utcnow()
        ))
    return out

@app.post("/bookings/cancel/{booking_id}")
def cancel_booking(booking_id: int, db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.booking_id == booking_id,
                                       Booking.status != "Cancelled").first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.status == "Cancelled":
        return {"message":f"Booking {booking_id} already cancelled"}
    
    booking.status = "Cancelled"
    db.commit()
    return {"message": f"Booking {booking_id} cancelled successfully"}

@app.get("/bookings/{identifier}", response_model=BookingResponse)
def get_booking(identifier: str, passenger_id: Optional[int] = Query(None, description="Optional passenger id to check ownership"), db: Session = Depends(get_db)):
    """
    Fetch a booking by numeric booking_id or by PNR string.
    If passenger_id is provided, enforce ownership (403 otherwise).
    Note: /bookings/me remains a separate explicit route and takes precedence.
    """
    if identifier.isdigit():
        b = db.query(Booking).filter(Booking.booking_id == int(identifier)).first()
    else:
        b = db.query(Booking).filter(Booking.pnr == identifier).first()

    if not b:
        raise HTTPException(status_code=404, detail="Booking not found")

    if passenger_id is not None and b.passenger_id != passenger_id:
        raise HTTPException(status_code=403, detail="Not authorized for this booking")

    flight_number = db.query(Flight.flight_number).filter(Flight.flight_id == b.flight_id).scalar()
    seat_number = db.query(Seat.seat_number).filter(Seat.seat_id == b.seat_id).scalar()
    passenger_name = db.query(Passenger.full_name).filter(Passenger.passenger_id == b.passenger_id).scalar()

    return BookingResponse(
        booking_id=b.booking_id,
        pnr=b.pnr,
        flight_number=flight_number or "",
        passenger_name=passenger_name or "",
        seat_number=seat_number or "",
        amount_paid=float(b.amount_paid),
        status=b.status,
        booking_date=b.booking_date or datetime.utcnow()
    )

@app.get("/bookings/me", response_model=List[BookingResponse])
def my_bookings(passenger_id: int = Query(..., description="ID of the passenger"), db: Session = Depends(get_db)):
    """
    Get all bookings for a given passenger.
    """
    rows = db.query(Booking).filter(Booking.passenger_id == passenger_id,
                    Booking.status != "Cancelled").all()
    out = []
    for b in rows:
        flight_number = db.query(Flight.flight_number).filter(Flight.flight_id == b.flight_id).scalar()
        seat_number = db.query(Seat.seat_number).filter(Seat.seat_id == b.seat_id).scalar()
        passenger_name = db.query(Passenger.full_name).filter(Passenger.passenger_id == b.passenger_id).scalar()
        out.append(BookingResponse(
            booking_id=b.booking_id,
            pnr=b.pnr,
            flight_number=flight_number or "",
            passenger_name=passenger_name or "",
            seat_number=seat_number or "",
            amount_paid=float(b.amount_paid),
            status=b.status,
            booking_date=b.booking_date or datetime.utcnow()
        ))
    return out

@app.delete("/bookings/{pnr}")
def cancel_by_pnr(pnr: str, passenger_id: int = Query(..., description="ID of the passenger"), db: Session = Depends(get_db)):
    """
    Cancel booking by PNR:
      - passenger_id is required
      - set booking.status = 'Cancelled' and free seat (is_booked=0)
      - keep booking row for history
    """
    try:
        with db.begin():
            booking = db.query(Booking).filter(Booking.pnr == pnr).with_for_update().first()
            if not booking:
                raise HTTPException(status_code=404, detail="Booking not found")
            if booking.passenger_id != passenger_id:
                raise HTTPException(status_code=403, detail="Not authorized to cancel this booking")
            if booking.status == "Cancelled":
                return {"message": f"Booking {pnr} already cancelled"}

            # free seat
            seat = db.query(Seat).filter(Seat.seat_id == booking.seat_id).with_for_update().first()
            if seat:
                seat.is_booked = 0
                db.add(seat)

            booking.status = "Cancelled"
            db.add(booking)
            return {"message": f"Booking {pnr} cancelled successfully", "booking_id": booking.booking_id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Cancellation failed: {e}")



@app.get("/", include_in_schema=False)
def _health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


@app.get("/debug/bookings/recent")
def debug_recent_bookings(limit: int = 20, db: Session = Depends(get_db)):
    rows = db.query(Booking).order_by(Booking.booking_date.desc()).limit(limit).all()
    return [{
        "booking_id": r.booking_id,
        "passenger_id": r.passenger_id,
        "flight_id": r.flight_id,
        "seat_id": r.seat_id,
        "status": r.status,
        "pnr": r.pnr,
        "booking_date": r.booking_date
    } for r in rows]

