"""
Music API for TripTunes.

Loads songs from the database, builds the MusicTrie fresh per request
(cheap for a few hundred songs), and exposes search / autocomplete /
artist / full-text / playlist endpoints backed by music.py.
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db, Song as SongRow
import music as logic

router = APIRouter(prefix="/api/music", tags=["music"])


class SongOut(BaseModel):
    id: int
    name: str
    artist: str
    genre: str
    mood: str
    rating: float


def _load(db: Session) -> list:
    rows = db.query(SongRow).all()
    return [logic.Song(id=r.id, name=r.name, artist=r.artist,
                       genre=r.genre, mood=r.mood, rating=r.rating) for r in rows]


def _out(songs) -> list:
    return [SongOut(id=s.id, name=s.name, artist=s.artist,
                    genre=s.genre, mood=s.mood, rating=s.rating) for s in songs]


def _trie(songs) -> logic.MusicTrie:
    t = logic.MusicTrie()
    for s in songs:
        t.insert(s)
    return t


@router.get("/search", response_model=list[SongOut])
def search(q: str = Query(""), db: Session = Depends(get_db)):
    songs = _load(db)
    if not q:
        return _out(logic.generate_playlist(songs, len(songs)))  # all, rating-sorted
    return _out(logic.kmp_search(songs, q))


@router.get("/autocomplete", response_model=list[SongOut])
def autocomplete(prefix: str = Query(...), limit: int = Query(8, ge=1, le=50),
                 db: Session = Depends(get_db)):
    return _out(_trie(_load(db)).autocomplete(prefix, limit))


@router.get("/by-artist", response_model=list[SongOut])
def by_artist(artist: str = Query(...), db: Session = Depends(get_db)):
    return _out(_trie(_load(db)).by_artist(artist))


@router.get("/filters")
def filters(db: Session = Depends(get_db)):
    songs = _load(db)
    return {
        "moods": sorted(set(s.mood for s in songs)),
        "genres": sorted(set(s.genre for s in songs)),
    }


class PlaylistResult(BaseModel):
    songs: list[SongOut]
    count: int


@router.get("/playlist", response_model=PlaylistResult)
def playlist(
    mood: str = Query(""),
    genre: str = Query(""),
    minutes: int = Query(60, ge=1),
    db: Session = Depends(get_db),
):
    songs = logic.filter_songs(_load(db), mood=mood, genre=genre)
    # ~4 minutes per song, same heuristic as the console version
    count = max(1, minutes // 4)
    picked = logic.generate_playlist(songs, count)
    return PlaylistResult(songs=_out(picked), count=len(picked))