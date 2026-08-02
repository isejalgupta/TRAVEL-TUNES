"""
Real-world route API for TripTunes.

Backed by geo.py (Nominatim + OSRM), so you can route between ANY two
real places - not a fixed list of cities. Two endpoints:

  GET /api/routes/geocode?q=   - type-ahead place search (autocomplete)
  GET /api/routes/path         - real driving route between two places

The path response carries the full road geometry so the map can trace
the actual roads, plus real distance, real drive time, and an estimated
cost (labelled as an estimate - see geo.py).
"""

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

import geo

router = APIRouter(prefix="/api/routes", tags=["routes"])


class Place(BaseModel):
    name: str
    display_name: str
    lat: float
    lng: float


class PathOut(BaseModel):
    source: Place
    destination: Place
    distance_km: float
    duration_min: int
    duration_text: str
    cost_est_inr: int
    coordinates: list[list[float]]  # [[lat, lng], ...] road line


@router.get("/geocode", response_model=list[Place])
def geocode(q: str = Query(..., min_length=2)):
    """Search real places by name for the autocomplete dropdown."""
    try:
        return [Place(**p) for p in geo.geocode(q, limit=6)]
    except geo.GeoError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/path", response_model=PathOut)
def path(
    source: str = Query(...),
    destination: str = Query(...),
    # Optional pre-resolved coordinates (e.g. from "Locate me"), so we can
    # skip geocoding when the caller already knows the exact point.
    src_lat: float = Query(None), src_lng: float = Query(None),
    dst_lat: float = Query(None), dst_lng: float = Query(None),
):
    try:
        if None not in (src_lat, src_lng, dst_lat, dst_lng):
            result = geo.route(src_lat, src_lng, dst_lat, dst_lng)
            result["source"] = {"name": source, "display_name": source,
                                "lat": src_lat, "lng": src_lng}
            result["destination"] = {"name": destination, "display_name": destination,
                                     "lat": dst_lat, "lng": dst_lng}
        else:
            result = geo.route_by_name(source, destination)
    except geo.GeoError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return PathOut(
        source=Place(**result["source"]),
        destination=Place(**result["destination"]),
        distance_km=result["distance_km"],
        duration_min=result["duration_min"],
        duration_text=geo.humanize_duration(result["duration_min"]),
        cost_est_inr=result["cost_est_inr"],
        coordinates=result["coordinates"],
    )
