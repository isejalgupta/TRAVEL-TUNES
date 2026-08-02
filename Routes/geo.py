import json
import time
import urllib.parse
import urllib.request

USER_AGENT = "TripTunes/1.0 (college project; contact: student@example.com)"
# Photon is an OSM-based geocoder built for autocomplete and is far more
# permissive than Nominatim's public server (which 403s automated calls).
# We try Photon first, then fall back to Nominatim.
PHOTON = "https://photon.komoot.io/api/"
NOMINATIM = "https://nominatim.openstreetmap.org/search"
OSRM = "https://router.project-osrm.org/route/v1/driving"
TIMEOUT = 15  # seconds

# Rough ₹/km fuel estimate for a car (~₹100/L at ~14 km/L). Adjust freely.
COST_PER_KM_INR = 7.0

# Tiny in-memory caches so repeated lookups don't hammer the free
# services (and so autocomplete feels instant on repeats).
_geocode_cache: dict[str, list] = {}
_route_cache: dict[str, dict] = {}


class GeoError(RuntimeError):
    """A geocoding or routing lookup failed (network, no result, etc.)."""


def _get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ------------------------------------------------------------------
#  Geocoding  (name -> coordinates)
# ------------------------------------------------------------------

def geocode(query: str, limit: int = 5) -> list[dict]:
    """Return up to `limit` places matching a typed query.

    Each result: {name, display_name, lat, lng}. Empty list if nothing
    matches. Tries Photon first, then Nominatim; raises GeoError only if
    both providers fail with a network/HTTP error.
    """
    query = (query or "").strip()
    if len(query) < 2:
        return []

    key = f"{query.lower()}|{limit}"
    if key in _geocode_cache:
        return _geocode_cache[key]

    errors = []
    for provider in (_geocode_photon, _geocode_nominatim):
        try:
            results = provider(query, limit)
            _geocode_cache[key] = results
            return results
        except Exception as exc:
            errors.append(f"{provider.__name__}: {exc}")

    raise GeoError("Place search failed (" + "; ".join(errors) + ")")


def _geocode_photon(query: str, limit: int) -> list[dict]:
    params = urllib.parse.urlencode({"q": query, "limit": limit, "lang": "en"})
    data = _get_json(f"{PHOTON}?{params}")
    results = []
    for feat in data.get("features", []):
        try:
            lon, lat = feat["geometry"]["coordinates"][:2]
            p = feat.get("properties", {})
            # Build a readable label, dropping blanks and duplicates.
            parts = [p.get("name"), p.get("city"), p.get("county"),
                     p.get("state"), p.get("country")]
            label = ", ".join(dict.fromkeys([x for x in parts if x]))
            results.append({
                "name": p.get("name") or (label.split(",")[0] if label else query),
                "display_name": label or (p.get("name") or query),
                "lat": float(lat),
                "lng": float(lon),
            })
        except (KeyError, ValueError, TypeError):
            continue
    return results


def _geocode_nominatim(query: str, limit: int) -> list[dict]:
    params = urllib.parse.urlencode({
        "q": query, "format": "jsonv2", "limit": limit, "addressdetails": 0,
    })
    rows = _get_json(f"{NOMINATIM}?{params}")
    results = []
    for r in rows:
        try:
            results.append({
                "name": r.get("name") or r.get("display_name", "").split(",")[0],
                "display_name": r.get("display_name", ""),
                "lat": float(r["lat"]),
                "lng": float(r["lon"]),
            })
        except (KeyError, ValueError):
            continue
    return results


def geocode_one(query: str) -> dict | None:
    """Best single match for a place name, or None."""
    results = geocode(query, limit=1)
    return results[0] if results else None


# ------------------------------------------------------------------
#  Routing  (coordinates -> real road route)
# ------------------------------------------------------------------

def route(src_lat: float, src_lng: float, dst_lat: float, dst_lng: float) -> dict:
    """Real driving route between two points.

    Returns:
      {
        distance_km, duration_min, cost_est_inr,
        coordinates: [[lat, lng], ...]   # the road line, for the map
      }
    Raises GeoError if OSRM can't find a route.
    """
    key = f"{src_lat:.4f},{src_lng:.4f};{dst_lat:.4f},{dst_lng:.4f}"
    if key in _route_cache:
        # Return a shallow copy: callers (route_by_name, the API) attach
        # 'source'/'destination' to the result, and mutating the cached
        # dict itself would leak those across concurrent requests.
        return dict(_route_cache[key])

    # OSRM wants lon,lat order.
    coords = f"{src_lng},{src_lat};{dst_lng},{dst_lat}"
    url = f"{OSRM}/{coords}?overview=full&geometries=geojson"
    try:
        data = _get_json(url)
    except Exception as exc:
        raise GeoError(f"Routing failed: {exc}") from exc

    if data.get("code") != "Ok" or not data.get("routes"):
        raise GeoError("No drivable route between those points.")

    r = data["routes"][0]
    distance_km = r["distance"] / 1000.0
    duration_min = r["duration"] / 60.0
    # GeoJSON gives [lon, lat]; flip to [lat, lng] for Leaflet.
    line = [[c[1], c[0]] for c in r["geometry"]["coordinates"]]

    result = {
        "distance_km": round(distance_km, 1),
        "duration_min": round(duration_min),
        "cost_est_inr": round(distance_km * COST_PER_KM_INR),
        "coordinates": line,
    }
    _route_cache[key] = result
    # Hand back a copy so the caller's added keys never touch the cache.
    return dict(result)


def route_by_name(source: str, destination: str) -> dict:
    """Geocode two place names, then route between them.

    Adds the resolved 'source' and 'destination' place dicts to the
    result so callers can show exactly which places were matched.
    """
    src = geocode_one(source)
    if src is None:
        raise GeoError(f"Couldn't find a place called '{source}'.")
    dst = geocode_one(destination)
    if dst is None:
        raise GeoError(f"Couldn't find a place called '{destination}'.")

    result = route(src["lat"], src["lng"], dst["lat"], dst["lng"])
    result["source"] = src
    result["destination"] = dst
    return result


def humanize_duration(minutes: float) -> str:
    """'1470' -> '24 h 30 min'."""
    minutes = int(round(minutes))
    h, m = divmod(minutes, 60)
    if h and m:
        return f"{h} h {m} min"
    if h:
        return f"{h} h"
    return f"{m} min"
