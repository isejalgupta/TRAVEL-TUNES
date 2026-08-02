import os
import sys
from contextlib import asynccontextmanager

# The feature modules were organised into subfolders (Activities/, ChatBot/,
# Music/, Routes/) but they import each other by flat module name
# (`import geo`, `from auth import ...`). Rather than rewrite every import,
# we add those folders to the import path here, before any of them load.
# database.py / auth.py stay in the project root, which is already on the path.
_ROOT = os.path.dirname(os.path.abspath(__file__))
for _sub in ("Activities", "ChatBot", "Music", "Routes"):
    _path = os.path.join(_ROOT, _sub)
    if _path not in sys.path:
        sys.path.insert(0, _path)

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from database import init_db
import auth
import trips
import activities_api
import music_api
import frequency_api
import routes_api
import chat_api
from activitiesdata import seed_activities
from musicdata import seed_songs


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_activities()
    seed_songs()
    yield


app = FastAPI(title="TripTunes API", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(trips.router)
app.include_router(activities_api.router)
app.include_router(music_api.router)
app.include_router(frequency_api.router)
app.include_router(routes_api.router)
app.include_router(chat_api.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.mount("/", StaticFiles(directory=".", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)