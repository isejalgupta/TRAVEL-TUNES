
from datetime import date, timedelta

from langchain_core.tools import tool

from database import (
    SessionLocal, Activity as ActivityRow, Song as SongRow,
    Trip, TripDay, TripActivity,
)
import activities as activity_logic
import music as music_logic
import activity_ai
import geo


# ------------------------------------------------------------------
#  Loading helpers - db rows -> the plain dataclasses your logic uses
# ------------------------------------------------------------------

def _load_activities(db, city: str | None = None) -> list:
    if city:
        # Generate + cache with the AI if we don't have this city yet, so
        # Trippy can answer for anywhere - same behaviour as the web UI.
        try:
            rows = activity_ai.ensure_city(db, city)
        except activity_ai.ActivityGenError:
            rows = []
    else:
        rows = db.query(ActivityRow).all()
    return [
        activity_logic.Activity(
            id=r.id, name=r.name, location=r.location, category=r.category,
            cost=r.cost, rating=r.rating, duration=r.duration,
        )
        for r in rows
    ]


def _load_songs(db) -> list:
    return [
        music_logic.Song(id=r.id, name=r.name, artist=r.artist,
                         genre=r.genre, mood=r.mood, rating=r.rating)
        for r in db.query(SongRow).all()
    ]


def _fmt_activities(items: list) -> str:
    if not items:
        return "No activities matched."
    lines = [
        f"- {a.name} ({a.category}) - Rs.{a.cost:.0f}, "
        f"{a.duration:.1f}h, rated {a.rating}"
        for a in items
    ]
    return "\n".join(lines)


def _fmt_songs(items: list) -> str:
    if not items:
        return "No songs matched."
    return "\n".join(
        f"- {s.name} by {s.artist} ({s.genre}, {s.mood}, rated {s.rating})"
        for s in items
    )


# ------------------------------------------------------------------
#  Tool factory
# ------------------------------------------------------------------

def build_tools(user_id: int | None) -> list:
    """Return the tool list for one request.

    user_id is None for anonymous visitors - the trip tools then refuse
    politely instead of erroring, and the agent tells the user to log in.
    """

    # --------------------------------------------------------------
    #  Destinations and activities
    # --------------------------------------------------------------

    @tool
    def list_destinations() -> str:
        """List every city TripTunes has activity data for. Use this first
        if the user asks a vague question like 'where can I go?', or to
        check whether a city they named is actually supported."""
        db = SessionLocal()
        try:
            rows = db.query(ActivityRow.location).distinct().all()
            cities = sorted(r[0] for r in rows)
            return "Supported destinations: " + ", ".join(cities) if cities else "No destinations loaded."
        finally:
            db.close()

    @tool
    def find_activities(city: str, max_cost: float = None,
                        min_rating: float = None, max_duration: float = None) -> str:
        """Find things to do in a city, best-rated first, with optional
        filters. Use for 'what can I do in Jaipur', 'cheap things in Goa',
        'top rated attractions in Delhi'. Costs are in rupees, duration in
        hours. Leave a filter as None to ignore it."""
        db = SessionLocal()
        try:
            items = _load_activities(db, city)
            if not items:
                return (f"No activities found for '{city}'. "
                        f"Call list_destinations to see supported cities.")
            items = activity_logic.filter_activities(
                items, max_cost=max_cost, min_rating=min_rating, max_duration=max_duration
            )
            items = activity_logic.sort_by_rating(items)
            return f"Activities in {city}:\n" + _fmt_activities(items)
        finally:
            db.close()

    @tool
    def plan_within_budget(city: str, budget: float) -> str:
        """Pick the best possible set of activities in a city for a given
        budget in rupees. Uses a 0/1 knapsack algorithm to maximise total
        rating without going over budget. Use when the user gives a budget,
        e.g. 'what can I do in Delhi with 200 rupees'."""
        db = SessionLocal()
        try:
            items = _load_activities(db, city)
            if not items:
                return f"No activities found for '{city}'."
            picked = activity_logic.budget_optimizer(items, budget)
            if not picked:
                return f"Nothing in {city} fits a budget of Rs.{budget:.0f}."
            total = sum(a.cost for a in picked)
            return (f"Best picks in {city} within Rs.{budget:.0f} "
                    f"(knapsack optimiser):\n{_fmt_activities(picked)}\n"
                    f"Total cost: Rs.{total:.0f}, "
                    f"total time: {sum(a.duration for a in picked):.1f}h")
        finally:
            db.close()

    @tool
    def plan_day_schedule(city: str, hours: float, budget: float) -> str:
        """Build the best one-day plan for a city given both a time limit
        (hours) and a money limit (rupees). Uses backtracking search to
        maximise total rating within both constraints. Use for 'plan my
        day in Mumbai, 8 hours and 500 rupees'."""
        db = SessionLocal()
        try:
            items = _load_activities(db, city)
            if not items:
                return f"No activities found for '{city}'."
            picked = activity_logic.optimal_schedule(items, hours, budget)
            if not picked:
                return f"Nothing in {city} fits {hours}h and Rs.{budget:.0f}."
            return (f"Suggested day in {city} ({hours}h, Rs.{budget:.0f}):\n"
                    f"{_fmt_activities(picked)}\n"
                    f"Total: Rs.{sum(a.cost for a in picked):.0f}, "
                    f"{sum(a.duration for a in picked):.1f}h")
        finally:
            db.close()

    # --------------------------------------------------------------
    #  Routes  (Dijkstra)
    # --------------------------------------------------------------

    @tool
    def find_route(origin: str, destination: str) -> str:
        """Find the real driving route between ANY two real places -
        cities, towns, even landmarks, anywhere (not limited to a fixed
        list). Returns the real road distance, real drive time, and an
        estimated fuel cost. Use for 'how do I get from Bangalore to
        Chennai', 'distance from Manali to Leh', 'route to Goa'. The cost
        is an estimate (distance x a per-km rate), so present it as such."""
        try:
            result = geo.route_by_name(origin, destination)
        except geo.GeoError as exc:
            return str(exc)

        src = result["source"]["display_name"] or origin
        dst = result["destination"]["display_name"] or destination
        return (
            f"Driving route found (real roads, via OpenStreetMap):\n"
            f"From: {src}\n"
            f"To: {dst}\n"
            f"Distance: {result['distance_km']} km\n"
            f"Drive time: {geo.humanize_duration(result['duration_min'])}\n"
            f"Estimated fuel cost: about Rs.{result['cost_est_inr']} "
            f"(rough estimate, not a real fare)."
        )

    # --------------------------------------------------------------
    #  Music
    # --------------------------------------------------------------

    @tool
    def search_songs(query: str) -> str:
        """Search the song library by title or artist text. Uses KMP
        substring matching. Use for 'do you have any Arijit Singh songs',
        'find songs with dil in the name'."""
        db = SessionLocal()
        try:
            found = music_logic.kmp_search(_load_songs(db), query)
            return f"Songs matching '{query}':\n" + _fmt_songs(found[:15])
        finally:
            db.close()

    @tool
    def list_music_options() -> str:
        """List the available song moods and genres. Use this before
        building a playlist if you're unsure what values are valid."""
        db = SessionLocal()
        try:
            songs = _load_songs(db)
            moods = sorted({s.mood for s in songs})
            genres = sorted({s.genre for s in songs})
            return f"Moods: {', '.join(moods)}\nGenres: {', '.join(genres)}"
        finally:
            db.close()

    @tool
    def build_playlist(mood: str = "", genre: str = "", minutes: int = 60) -> str:
        """Build a playlist for a journey. Filters by mood and/or genre
        (leave blank for any) and sizes it to the trip length in minutes,
        assuming roughly 4 minutes per song, picking the highest rated.
        Use for 'playlist for a 3 hour drive to Goa', 'romantic songs for
        the trip'. Call list_music_options first if unsure of valid values."""
        db = SessionLocal()
        try:
            songs = music_logic.filter_songs(_load_songs(db), mood=mood, genre=genre)
            if not songs:
                return (f"No songs for mood='{mood}' genre='{genre}'. "
                        f"Call list_music_options for valid values.")
            count = max(1, int(minutes) // 4)
            picked = music_logic.generate_playlist(songs, count)
            return (f"Playlist ({len(picked)} songs, ~{len(picked) * 4} min):\n"
                    + _fmt_songs(picked))
        finally:
            db.close()

    # --------------------------------------------------------------
    #  The user's own trips  (scoped to user_id, never exposed to the LLM)
    # --------------------------------------------------------------

    @tool
    def get_my_trips() -> str:
        """List the trips saved by the currently logged-in user, with their
        ids and dates. Call this before modifying a trip, so you know the
        right trip id. Use for 'what trips do I have', 'show my Goa trip'."""
        if user_id is None:
            return "The user isn't logged in, so they have no saved trips. Ask them to log in."
        db = SessionLocal()
        try:
            trips = db.query(Trip).filter(Trip.user_id == user_id).all()
            if not trips:
                return "No saved trips yet."
            return "Saved trips:\n" + "\n".join(
                f"- id={t.id}: {t.name}, {t.start_date} to {t.end_date} ({len(t.days)} days)"
                for t in trips
            )
        finally:
            db.close()

    @tool
    def get_trip_details(trip_id: int) -> str:
        """Show the full day-by-day itinerary of one saved trip, including
        every planned activity and the running totals."""
        if user_id is None:
            return "The user isn't logged in. Ask them to log in."
        db = SessionLocal()
        try:
            trip = db.query(Trip).filter(Trip.id == trip_id,
                                         Trip.user_id == user_id).first()
            if trip is None:
                return f"No trip with id {trip_id} belongs to this user."
            out = [f"{trip.name} ({trip.start_date} to {trip.end_date}):"]
            cost = duration = 0.0
            for day in sorted(trip.days, key=lambda d: d.day_number):
                out.append(f"Day {day.day_number} ({day.date}):")
                if not day.activities:
                    out.append("  (nothing planned)")
                for a in day.activities:
                    out.append(f"  - {a.name}, Rs.{a.cost:.0f}, {a.duration:.1f}h")
                    cost += a.cost
                    duration += a.duration
            out.append(f"Totals: Rs.{cost:.0f}, {duration:.1f}h")
            return "\n".join(out)
        finally:
            db.close()

    @tool
    def create_trip(name: str, start_date: str, end_date: str) -> str:
        """Create and save a new trip for the logged-in user. Dates must be
        YYYY-MM-DD and cannot be in the past. One day is generated
        automatically per date in the range. Confirm the details with the
        user before calling this, since it writes to their account."""
        if user_id is None:
            return "The user isn't logged in, so a trip can't be saved. Ask them to log in first."

        try:
            start = date.fromisoformat(start_date)
            end = date.fromisoformat(end_date)
        except ValueError:
            return "Dates must be in YYYY-MM-DD format."
        if start < date.today():
            return "The start date is in the past. Ask the user for a future date."
        if end < start:
            return "The end date is before the start date."
        if not name.strip():
            return "The trip needs a name."

        db = SessionLocal()
        try:
            trip = Trip(user_id=user_id, name=name.strip(),
                        start_date=start_date, end_date=end_date)
            db.add(trip)
            db.flush()

            current, number = start, 1
            while current <= end and number <= 365:
                db.add(TripDay(trip_id=trip.id, day_number=number,
                               date=current.isoformat()))
                current += timedelta(days=1)
                number += 1

            db.commit()
            return (f"Created trip '{trip.name}' (id={trip.id}) with "
                    f"{number - 1} day(s), {start_date} to {end_date}.")
        finally:
            db.close()

    @tool
    def add_activity_to_trip(trip_id: int, day_number: int, name: str,
                             duration: float, cost: float) -> str:
        """Add one activity to a specific day of a saved trip. Get the
        trip_id from get_my_trips first. duration is in hours, cost in
        rupees - take these from find_activities rather than guessing."""
        if user_id is None:
            return "The user isn't logged in. Ask them to log in first."
        db = SessionLocal()
        try:
            trip = db.query(Trip).filter(Trip.id == trip_id,
                                         Trip.user_id == user_id).first()
            if trip is None:
                return f"No trip with id {trip_id} belongs to this user."
            day = db.query(TripDay).filter(TripDay.trip_id == trip.id,
                                           TripDay.day_number == day_number).first()
            if day is None:
                return f"Trip {trip_id} has no day {day_number}."
            db.add(TripActivity(day_id=day.id, name=name.strip(),
                                duration=duration, cost=cost))
            db.commit()
            return f"Added '{name}' to day {day_number} of '{trip.name}'."
        finally:
            db.close()

    return [
        list_destinations, find_activities, plan_within_budget, plan_day_schedule,
        find_route,
        search_songs, list_music_options, build_playlist,
        get_my_trips, get_trip_details, create_trip, add_activity_to_trip,
    ]
