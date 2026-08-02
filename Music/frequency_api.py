"""
Song frequency tracker for TripTunes.

Per-user play counts, backed by the PlayCount table. Ports the console
FrequencyTracker: increment on play, view a song's count, list the
most-played, and reset. Every route is login-protected so counts are
private to each user.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db, PlayCount, Song as SongRow, User
from auth import get_current_user

router = APIRouter(prefix="/api/frequency", tags=["frequency"])


class PlayResult(BaseModel):
    song_id: int
    name: str
    artist: str
    count: int


class MostPlayedItem(BaseModel):
    name: str
    artist: str
    count: int


def _increment_play(user_id: int, song_id: int, db: Session) -> int:
    """Increment a user's play count for a song and return the new total.

    The (user_id, song_id) unique constraint guarantees a single row. If
    two concurrent requests both try to INSERT the first play, one wins
    and the other hits an IntegrityError - we catch it, roll back, and
    re-read the now-existing row, so the count is never split.
    """
    row = db.query(PlayCount).filter(
        PlayCount.user_id == user_id, PlayCount.song_id == song_id
    ).first()
    if row is None:
        row = PlayCount(user_id=user_id, song_id=song_id, count=1)
        db.add(row)
        try:
            db.commit()
            return row.count
        except IntegrityError:
            db.rollback()
            row = db.query(PlayCount).filter(
                PlayCount.user_id == user_id, PlayCount.song_id == song_id
            ).first()

    row.count += 1
    db.commit()
    return row.count


@router.post("/play/{song_id}", response_model=PlayResult)
def play_song(song_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    song = db.query(SongRow).filter(SongRow.id == song_id).first()
    if song is None:
        raise HTTPException(status_code=404, detail="Song not found.")
    count = _increment_play(user.id, song_id, db)
    return PlayResult(song_id=song_id, name=song.name, artist=song.artist, count=count)


@router.get("/count/{song_id}", response_model=PlayResult)
def get_count(song_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    song = db.query(SongRow).filter(SongRow.id == song_id).first()
    if song is None:
        raise HTTPException(status_code=404, detail="Song not found.")
    row = db.query(PlayCount).filter(
        PlayCount.user_id == user.id, PlayCount.song_id == song_id
    ).first()
    count = row.count if row else 0
    return PlayResult(song_id=song_id, name=song.name, artist=song.artist, count=count)


@router.get("/most-played", response_model=list[MostPlayedItem])
def most_played(limit: int = 10, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(PlayCount, SongRow)
        .join(SongRow, PlayCount.song_id == SongRow.id)
        .filter(PlayCount.user_id == user.id, PlayCount.count > 0)
        .order_by(PlayCount.count.desc())
        .limit(limit)
        .all()
    )
    return [MostPlayedItem(name=s.name, artist=s.artist, count=pc.count) for pc, s in rows]


@router.delete("/reset")
def reset(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(PlayCount).filter(PlayCount.user_id == user.id).delete()
    db.commit()
    return {"reset": True}