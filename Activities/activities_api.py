"""
Activities API for TripTunes.

Reads activities from the database, converts them to the plain
Activity dataclass, and runs the logic in activities.py. Public
browsing endpoints don't require login; the optimiser endpoints
don't either, but could be gated later.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db, Activity as ActivityRow
import activities as logic
import activity_ai

router = APIRouter(prefix="/api/activities", tags=["activities"])


def _rows_for(city: str, db: Session):
    """Activities for a city - generating them with the AI on first request
    for a city we don't have yet. Raises the right HTTP error otherwise."""
    try:
        rows = activity_ai.ensure_city(db, city)
    except activity_ai.ActivityGenError as exc:
        # AI not configured, or it couldn't produce a usable list.
        raise HTTPException(
            status_code=503,
            detail=f"Couldn't get activities for '{city}'. {exc}",
        )
    if not rows:
        raise HTTPException(status_code=404, detail=f"No activities found for {city}.")
    return rows


class ActivityOut(BaseModel):
    id: int
    name: str
    location: str
    category: str
    cost: float
    rating: float
    duration: float


def _to_logic(rows) -> list:
    return [
        logic.Activity(id=r.id, name=r.name, location=r.location,
                       category=r.category, cost=r.cost, rating=r.rating,
                       duration=r.duration)
        for r in rows
    ]


def _out(items) -> list:
    return [ActivityOut(**a.__dict__) for a in items]


@router.get("/cities", response_model=list[str])
def list_cities(db: Session = Depends(get_db)):
    rows = db.query(ActivityRow.location).distinct().all()
    return sorted(r[0] for r in rows)


@router.get("", response_model=list[ActivityOut])
def list_activities(
    city: str = Query(...),
    sort: str = Query("rating", pattern="^(rating|cost|duration)$"),
    db: Session = Depends(get_db),
):
    rows = _rows_for(city, db)
    items = _to_logic(rows)
    if sort == "rating":
        items = logic.sort_by_rating(items)
    elif sort == "cost":
        items = logic.sort_by_cost(items)
    else:
        items = logic.sort_by_duration(items)
    return _out(items)


class OptimizeResult(BaseModel):
    activities: list[ActivityOut]
    total_cost: float
    total_rating: float
    total_duration: float


def _summarize(items) -> OptimizeResult:
    return OptimizeResult(
        activities=_out(items),
        total_cost=sum(a.cost for a in items),
        total_rating=round(sum(a.rating for a in items), 2),
        total_duration=sum(a.duration for a in items),
    )


@router.get("/optimize/budget", response_model=OptimizeResult)
def optimize_budget(
    city: str = Query(...),
    max_budget: float = Query(..., ge=0),
    db: Session = Depends(get_db),
):
    rows = _rows_for(city, db)
    picked = logic.budget_optimizer(_to_logic(rows), max_budget)
    return _summarize(picked)


@router.get("/optimize/schedule", response_model=OptimizeResult)
def optimize_schedule(
    city: str = Query(...),
    max_hours: float = Query(..., ge=0),
    max_budget: float = Query(..., ge=0),
    db: Session = Depends(get_db),
):
    rows = _rows_for(city, db)
    picked = logic.optimal_schedule(_to_logic(rows), max_hours, max_budget)
    return _summarize(picked)


@router.get("/filter", response_model=list[ActivityOut])
def filter_acts(
    city: str = Query(...),
    max_cost: float = Query(None),
    min_rating: float = Query(None),
    max_duration: float = Query(None),
    db: Session = Depends(get_db),
):
    rows = _rows_for(city, db)
    items = logic.filter_activities(_to_logic(rows), max_cost=max_cost,
                                    min_rating=min_rating, max_duration=max_duration)
    items = logic.sort_by_rating(items)
    return _out(items)