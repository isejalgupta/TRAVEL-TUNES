
import os
from datetime import datetime, timezone

import bcrypt
from sqlalchemy import create_engine, ForeignKey, String, Float, UniqueConstraint
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
)

DATABASE_URL = os.environ.get("TRIPTUNES_DATABASE_URL", "sqlite:///./triptunes.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


# ------------------------------------------------------------------
#  Users
# ------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    # Display name / username. Nullable so accounts created before this
    # column existed still load; new signups always provide one.
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    trips: Mapped[list["Trip"]] = relationship(back_populates="owner", cascade="all, delete-orphan")

    def set_password(self, raw_password: str):
        hashed = bcrypt.hashpw(raw_password.encode("utf-8"), bcrypt.gensalt())
        self.hashed_password = hashed.decode("utf-8")

    def verify_password(self, raw_password: str) -> bool:
        return bcrypt.checkpw(raw_password.encode("utf-8"), self.hashed_password.encode("utf-8"))


# ------------------------------------------------------------------
#  (The old City / RouteEdge graph models were removed: routing now uses
#  real OpenStreetMap data via geo.py, not a seeded in-database graph.)
# ------------------------------------------------------------------
#  Activities
# ------------------------------------------------------------------

class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    location: Mapped[str] = mapped_column(String(100), index=True)
    category: Mapped[str] = mapped_column(String(50))
    cost: Mapped[float] = mapped_column(Float)
    rating: Mapped[float] = mapped_column(Float)
    duration: Mapped[float] = mapped_column(Float)


# ------------------------------------------------------------------
#  Music
# ------------------------------------------------------------------

class Song(Base):
    __tablename__ = "songs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), index=True)
    artist: Mapped[str] = mapped_column(String(150))
    genre: Mapped[str] = mapped_column(String(50))
    mood: Mapped[str] = mapped_column(String(50))
    rating: Mapped[float] = mapped_column(Float)


class PlayCount(Base):
    __tablename__ = "play_counts"
    # One row per (user, song): prevents duplicate rows that would split a
    # song's play count under concurrent /frequency/play requests.
    __table_args__ = (UniqueConstraint("user_id", "song_id", name="uq_play_user_song"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id"))
    count: Mapped[int] = mapped_column(default=0)


# ------------------------------------------------------------------
#  Trips / itineraries
# ------------------------------------------------------------------

class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(150))
    start_date: Mapped[str] = mapped_column(String(10))
    end_date: Mapped[str] = mapped_column(String(10))

    owner: Mapped["User"] = relationship(back_populates="trips")
    days: Mapped[list["TripDay"]] = relationship(back_populates="trip", cascade="all, delete-orphan")


class TripDay(Base):
    __tablename__ = "trip_days"

    id: Mapped[int] = mapped_column(primary_key=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id"))
    day_number: Mapped[int]
    date: Mapped[str] = mapped_column(String(10))

    trip: Mapped["Trip"] = relationship(back_populates="days")
    activities: Mapped[list["TripActivity"]] = relationship(back_populates="day", cascade="all, delete-orphan")


class TripActivity(Base):
    __tablename__ = "trip_activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    day_id: Mapped[int] = mapped_column(ForeignKey("trip_days.id"))
    name: Mapped[str] = mapped_column(String(150))
    duration: Mapped[float] = mapped_column(Float)
    cost: Mapped[float] = mapped_column(Float)

    day: Mapped["TripDay"] = relationship(back_populates="activities")


# ------------------------------------------------------------------
#  Setup helpers
# ------------------------------------------------------------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    _migrate_add_user_name()
    _migrate_playcount_unique()


def _migrate_add_user_name():
    """Add users.name to databases created before the column existed.

    create_all() only CREATEs missing tables - it never ALTERs an
    existing one. So an older triptunes.db keeps a users table with no
    'name' column, and every query on it would fail. This tops up the
    column in place (SQLite ADD COLUMN is safe and instant), leaving all
    existing rows with name = NULL.
    """
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return
    columns = {c["name"] for c in inspector.get_columns("users")}
    if "name" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN name VARCHAR(100)"))


def _migrate_playcount_unique():
    """Collapse duplicate (user, song) play rows, then enforce uniqueness.

    Older databases could hold several rows for the same user+song (a race
    in /frequency/play), splitting the count. We merge those into a single
    row summing their counts, then add a unique index so it can't recur.
    Idempotent: the index is only created once, and dedupe is a no-op when
    there are no duplicates.
    """
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if "play_counts" not in inspector.get_table_names():
        return

    with engine.begin() as conn:
        # Merge duplicates: keep the lowest id per (user_id, song_id) and
        # give it the summed count, then delete the extras.
        conn.execute(text("""
            UPDATE play_counts
               SET count = (
                   SELECT SUM(p2.count) FROM play_counts p2
                    WHERE p2.user_id = play_counts.user_id
                      AND p2.song_id = play_counts.song_id
               )
             WHERE id IN (
                   SELECT MIN(id) FROM play_counts
                   GROUP BY user_id, song_id
             )
        """))
        conn.execute(text("""
            DELETE FROM play_counts
             WHERE id NOT IN (
                   SELECT MIN(id) FROM play_counts
                   GROUP BY user_id, song_id
             )
        """))
        conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_play_user_song "
            "ON play_counts(user_id, song_id)"
        ))