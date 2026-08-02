"""
Trip / itinerary API for TripTunes.

CRUD for trips owned by the logged-in user. Mirrors the ItineraryTree
from the original console app: a trip has days, each day has activities.
Creating a trip auto-generates one TripDay per date in the range, just
like _build_days() did before.

Every route here is protected - it uses get_current_user, so a user
only ever sees and edits their own trips.
"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db, Trip, TripDay, TripActivity, User
from auth import get_current_user

router = APIRouter(prefix="/api/trips", tags=["trips"])


# ------------------------------------------------------------------
#  Request / response shapes
# ------------------------------------------------------------------

class TripCreate(BaseModel):
    name: str
    start_date: str  # "YYYY-MM-DD"
    end_date: str


class ActivityCreate(BaseModel):
    name: str
    duration: float
    cost: float


class ActivityOut(BaseModel):
    id: int
    name: str
    duration: float
    cost: float


class DayOut(BaseModel):
    id: int
    day_number: int
    date: str
    activities: list[ActivityOut]


class TripSummary(BaseModel):
    id: int
    name: str
    start_date: str
    end_date: str
    day_count: int


class TripDetail(BaseModel):
    id: int
    name: str
    start_date: str
    end_date: str
    days: list[DayOut]
    total_cost: float
    total_duration: float


# ------------------------------------------------------------------
#  Helpers
# ------------------------------------------------------------------

def _parse(d: str) -> date:
    try:
        return date.fromisoformat(d)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid date '{d}', expected YYYY-MM-DD.")


def _owned_trip(trip_id: int, user: User, db: Session) -> Trip:
    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == user.id).first()
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found.")
    return trip


def _serialize(trip: Trip) -> TripDetail:
    days = sorted(trip.days, key=lambda d: d.day_number)
    day_out = []
    total_cost = 0.0
    total_duration = 0.0
    for d in days:
        acts = []
        for a in d.activities:
            acts.append(ActivityOut(id=a.id, name=a.name, duration=a.duration, cost=a.cost))
            total_cost += a.cost
            total_duration += a.duration
        day_out.append(DayOut(id=d.id, day_number=d.day_number, date=d.date, activities=acts))
    return TripDetail(
        id=trip.id, name=trip.name, start_date=trip.start_date, end_date=trip.end_date,
        days=day_out, total_cost=total_cost, total_duration=total_duration,
    )


# ------------------------------------------------------------------
#  Endpoints
# ------------------------------------------------------------------

@router.get("", response_model=list[TripSummary])
def list_trips(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    trips = db.query(Trip).filter(Trip.user_id == user.id).all()
    return [
        TripSummary(id=t.id, name=t.name, start_date=t.start_date,
                    end_date=t.end_date, day_count=len(t.days))
        for t in trips
    ]


@router.post("", response_model=TripDetail)
def create_trip(body: TripCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    start = _parse(body.start_date)
    end = _parse(body.end_date)
    today = date.today()
    if start < today:
        raise HTTPException(status_code=400, detail="Start date can't be in the past.")
    if end < start:
        raise HTTPException(status_code=400, detail="End date must be on or after start date.")
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Trip name cannot be empty.")

    trip = Trip(user_id=user.id, name=body.name.strip(),
                start_date=body.start_date, end_date=body.end_date)
    db.add(trip)
    db.flush()  # get trip.id before adding days

    # auto-generate one day per date in the range (cap at 365 for safety)
    current = start
    day_number = 1
    while current <= end and day_number <= 365:
        db.add(TripDay(trip_id=trip.id, day_number=day_number, date=current.isoformat()))
        current += timedelta(days=1)
        day_number += 1

    db.commit()
    db.refresh(trip)
    return _serialize(trip)


@router.get("/{trip_id}", response_model=TripDetail)
def get_trip(trip_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _serialize(_owned_trip(trip_id, user, db))


@router.delete("/{trip_id}")
def delete_trip(trip_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    trip = _owned_trip(trip_id, user, db)
    db.delete(trip)
    db.commit()
    return {"deleted": trip_id}


@router.post("/{trip_id}/days/{day_number}/activities", response_model=TripDetail)
def add_activity(trip_id: int, day_number: int, body: ActivityCreate,
                 user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    trip = _owned_trip(trip_id, user, db)
    day = db.query(TripDay).filter(TripDay.trip_id == trip.id,
                                   TripDay.day_number == day_number).first()
    if day is None:
        raise HTTPException(status_code=404, detail=f"Day {day_number} not found in this trip.")
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Activity name cannot be empty.")

    db.add(TripActivity(day_id=day.id, name=body.name.strip(),
                        duration=body.duration, cost=body.cost))
    db.commit()
    db.refresh(trip)
    return _serialize(trip)


@router.put("/{trip_id}/activities/{activity_id}/move/{to_day_number}", response_model=TripDetail)
def move_activity(trip_id: int, activity_id: int, to_day_number: int,
                  user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    trip = _owned_trip(trip_id, user, db)
    activity = (
        db.query(TripActivity)
        .join(TripDay, TripActivity.day_id == TripDay.id)
        .filter(TripActivity.id == activity_id, TripDay.trip_id == trip.id)
        .first()
    )
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found in this trip.")
    target_day = db.query(TripDay).filter(
        TripDay.trip_id == trip.id, TripDay.day_number == to_day_number
    ).first()
    if target_day is None:
        raise HTTPException(status_code=404, detail=f"Day {to_day_number} not found in this trip.")
    activity.day_id = target_day.id
    db.commit()
    db.refresh(trip)
    return _serialize(trip)


@router.delete("/{trip_id}/activities/{activity_id}", response_model=TripDetail)
def remove_activity(trip_id: int, activity_id: int,
                    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    trip = _owned_trip(trip_id, user, db)
    activity = (
        db.query(TripActivity)
        .join(TripDay, TripActivity.day_id == TripDay.id)
        .filter(TripActivity.id == activity_id, TripDay.trip_id == trip.id)
        .first()
    )
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found in this trip.")
    db.delete(activity)
    db.commit()
    db.refresh(trip)
    return _serialize(trip)