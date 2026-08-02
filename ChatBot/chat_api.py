"""
Chat API for TripTunes.

Thin HTTP layer over chatbot.py, following the same shape as the other
_api modules: routes here do request/response handling only, the
thinking lives in chatbot.py and chat_tools.py.

Auth is optional on purpose. A logged-out visitor can still ask about
destinations, routes and music - they just can't save trips. If a token
is present we decode it and pass the user id down, which both unlocks
the trip tools and keeps each user's conversation history separate.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from jose import jwt, JWTError
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db, User
from auth import SECRET_KEY, ALGORITHM
import chatbot
import llm

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    tools_used: list[str]
    authenticated: bool


def optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    """Return the logged-in user, or None if there's no valid token.

    Deliberately never raises: a bad or expired token just degrades the
    chat to anonymous mode instead of blocking the conversation.
    """
    header = request.headers.get("Authorization", "")
    if not header.lower().startswith("bearer "):
        return None
    token = header.split(" ", 1)[1].strip()
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return db.query(User).filter(User.id == int(user_id)).first()
    except (JWTError, ValueError):
        return None


@router.get("/status")
def status():
    """Which model is configured and whether it's ready to use.

    The UI calls this on load so it can show a clear setup message
    instead of failing on the user's first message.
    """
    return llm.describe()


@router.post("", response_model=ChatResponse)
def send_message(body: ChatRequest, request: Request,
                 user: User | None = Depends(optional_user)):
    text = body.message.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    if len(text) > 2000:
        raise HTTPException(status_code=400, detail="Message is too long (max 2000 characters).")

    user_id = user.id if user else None
    display_name = (user.name or user.email.split("@")[0]) if user else None
    # Per-browser id for anonymous visitors, so their histories stay separate.
    anon_id = request.headers.get("X-Anon-Id") if user is None else None

    try:
        result = chatbot.chat(text, user_id=user_id, display_name=display_name,
                              session_key=anon_id)
    except llm.LLMNotConfigured as exc:
        # 503: the app is fine, the AI provider just isn't set up yet.
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        # Surface the provider's actual message - it's the difference
        # between "wrong model name", "invalid key" and "rate limited",
        # which all otherwise look identical. Trimmed so it stays readable
        # in a chat bubble; the full traceback is still in the server log.
        detail = str(exc).strip().replace("\n", " ")
        if len(detail) > 300:
            detail = detail[:300] + "..."
        raise HTTPException(
            status_code=502,
            detail=f"The AI service failed to respond ({type(exc).__name__}): {detail}",
        )

    return ChatResponse(
        reply=result["reply"],
        tools_used=result["tools_used"],
        authenticated=user is not None,
    )


@router.delete("/history")
def clear(request: Request, user: User | None = Depends(optional_user)):
    """Reset this session's conversation so the next message starts fresh."""
    anon_id = request.headers.get("X-Anon-Id") if user is None else None
    chatbot.clear_history(user.id if user else None, session_key=anon_id)
    return {"cleared": True}
