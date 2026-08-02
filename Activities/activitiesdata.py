"""
Seed the activities table from the original console dataset.

Idempotent: running it again won't duplicate rows (it skips if the
table already has activities). Called on startup from app.py.
"""

from database import SessionLocal, Activity as ActivityRow

# (name, location, category, cost, rating, duration) - subset of the
# original console data, covering several cities so the city dropdown
# has variety. Easy to extend later.
ACTIVITIES = [
    ("Red Fort", "Delhi", "History", 50, 4.7, 3),
    ("Qutub Minar", "Delhi", "History", 40, 4.6, 2),
    ("India Gate", "Delhi", "Sightseeing", 0, 4.5, 1),
    ("Humayun's Tomb", "Delhi", "History", 35, 4.7, 2),
    ("Chandni Chowk Food Walk", "Delhi", "Food", 0, 4.8, 2),
    ("Lotus Temple", "Delhi", "Spiritual", 0, 4.6, 1),
    ("Akshardham Temple", "Delhi", "Spiritual", 0, 4.8, 3),
    ("Taj Mahal", "Agra", "Sightseeing", 50, 5.0, 3),
    ("Agra Fort", "Agra", "History", 40, 4.6, 2),
    ("Fatehpur Sikri", "Agra", "History", 40, 4.5, 3),
    ("Mehtab Bagh Sunset", "Agra", "Nature", 30, 4.7, 1),
    ("Amber Fort", "Jaipur", "History", 100, 4.8, 3),
    ("Hawa Mahal", "Jaipur", "Sightseeing", 50, 4.7, 1),
    ("City Palace Jaipur", "Jaipur", "Culture", 200, 4.6, 2),
    ("Nahargarh Fort", "Jaipur", "History", 50, 4.5, 2),
    ("Gateway of India", "Mumbai", "Sightseeing", 0, 4.6, 1),
    ("Marine Drive", "Mumbai", "Sightseeing", 0, 4.7, 2),
    ("Elephanta Caves", "Mumbai", "History", 40, 4.5, 4),
    ("Siddhivinayak Temple", "Mumbai", "Spiritual", 0, 4.7, 1),
    ("Baga Beach", "Goa", "Nature", 0, 4.6, 4),
    ("Dudhsagar Falls", "Goa", "Nature", 400, 4.8, 6),
    ("Old Goa Churches", "Goa", "History", 0, 4.5, 2),
    ("Scuba Diving Goa", "Goa", "Adventure", 3000, 4.7, 3),
]


def seed_activities():
    db = SessionLocal()
    try:
        if db.query(ActivityRow).first() is not None:
            return  # already seeded
        for name, loc, cat, cost, rating, dur in ACTIVITIES:
            db.add(ActivityRow(name=name, location=loc, category=cat,
                               cost=cost, rating=rating, duration=dur))
        db.commit()
    finally:
        db.close()