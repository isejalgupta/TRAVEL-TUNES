
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage

from llm import build_llm, LLMNotConfigured  # noqa: F401  (re-exported for chat_api)
from chat_tools import build_tools


AGENT_API = None
try:  # LangChain >= 1.0
    from langchain.agents import create_agent  # type: ignore
    AGENT_API = "v1"
except ImportError:
    try:  # LangChain 0.x
        from langchain.agents import AgentExecutor, create_tool_calling_agent  # type: ignore
        AGENT_API = "legacy"
    except ImportError:
        try:  # 1.x users who installed the compatibility package
            from langchain_classic.agents import (  # type: ignore
                AgentExecutor, create_tool_calling_agent,
            )
            AGENT_API = "legacy"
        except ImportError:
            AGENT_API = None

# How many past messages to keep per session (2 = one full exchange).
MAX_HISTORY_MESSAGES = 20

# Cap the number of live sessions so memory can't grow without bound;
# when exceeded we drop the oldest one (insertion order).
MAX_SESSIONS = 500

# session_key (str) -> list of LangChain messages.
# The key isolates conversations: "user:<id>" for logged-in users, and a
# distinct "anon:<browser-id>" per anonymous visitor - so one logged-out
# user's context never bleeds into another's (which the old shared key 0
# allowed).
_memory: dict[str, list] = {}


def _session_key(user_id: int | None, session_key: str | None) -> str:
    """Resolve the memory bucket for this turn.

    A logged-in user is always keyed by id. An explicit session_key
    (the anonymous browser id) is used as-is. As a last resort we fall
    back to a single shared anon bucket - callers should pass a real one.
    """
    if user_id is not None:
        return f"user:{user_id}"
    if session_key:
        return f"anon:{session_key}"
    return "anon:shared"


SYSTEM_PROMPT = """You are Trippy, the fun, upbeat AI travel and music \
companion built into the TripTunes app. You help users plan trips across \
India and build playlists to match. You have a light, playful personality \
- a little witty, quick with a music or travel pun - but you never let the \
banter get in the way of giving a clear, useful answer.

How you work:
- You have tools that read the app's real database and run its planning \
algorithms. ALWAYS use a tool for anything factual: activities, prices, \
ratings, durations, routes, songs, or the user's saved trips.
- NEVER invent an activity, price, song, or route. If a tool returns \
nothing, say so plainly and suggest what the user could try instead.
- All costs are Indian rupees. Durations are in hours.
- The app covers a limited set of cities. If asked about a city you don't \
support, call list_destinations and offer the closest supported option.

Style:
- Be warm, brief and concrete. Lead with the answer.
- Format lists of activities or songs as short bullet points.
- After giving a plan, offer one useful next step (e.g. saving it as a \
trip, or a playlist for the journey) - but only one, and keep it to a \
single line.

Writing to the user's account:
- create_trip and add_activity_to_trip change the user's saved data. \
Confirm the specifics with the user before calling them.
- If a tool says the user isn't logged in, tell them to log in - don't \
retry the tool.
"""


def _system_prompt(display_name: str | None) -> str:
    """The base persona, plus the user's name so Trippy can greet them by
    it. Falls back gracefully when we don't know the name (logged out)."""
    if display_name:
        return SYSTEM_PROMPT + (
            f"\n\nThe user you're talking to is called {display_name}. "
            f"Greet them by name when it feels natural, but don't overdo it."
        )
    return SYSTEM_PROMPT


def _prompt(display_name: str | None) -> ChatPromptTemplate:
    """The prompt scaffold. agent_scratchpad is where the executor writes
    the running record of tool calls and their results during a turn."""
    return ChatPromptTemplate.from_messages([
        ("system", _system_prompt(display_name)),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ])


def build_agent(user_id: int | None, display_name: str | None = None, verbose: bool = False):
    """Assemble a ready-to-run agent for one user.

    Built per-request rather than once at startup because the tools close
    over user_id - that's what keeps one user's trips invisible to
    another's agent.
    """
    if AGENT_API is None:
        raise LLMNotConfigured(
            "LangChain's agent API wasn't found. Run:  pip install langchain  "
            "(or, on LangChain 1.x, pip install langchain-classic)"
        )

    llm = build_llm()
    tools = build_tools(user_id)

    if AGENT_API == "v1":
        # LangChain >= 1.0: returns a compiled LangGraph agent.
        return create_agent(model=llm, tools=tools,
                            system_prompt=_system_prompt(display_name))

    # LangChain 0.x
    agent = create_tool_calling_agent(llm, tools, _prompt(display_name))
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=verbose,          # True prints the reasoning trace - useful for a demo
        max_iterations=6,         # stop runaway tool loops
        handle_parsing_errors=True,
        return_intermediate_steps=True,
    )


def get_history(user_id: int | None, session_key: str | None = None) -> list:
    key = _session_key(user_id, session_key)
    if key not in _memory and len(_memory) >= MAX_SESSIONS:
        # Evict the oldest session to keep memory bounded.
        _memory.pop(next(iter(_memory)), None)
    return _memory.setdefault(key, [])


def clear_history(user_id: int | None, session_key: str | None = None):
    _memory[_session_key(user_id, session_key)] = []


def chat(message: str, user_id: int | None = None,
         display_name: str | None = None, session_key: str | None = None,
         verbose: bool = False) -> dict:
    """Run one turn of conversation.

    user_id scopes the tools (a user's own trips); session_key scopes the
    conversation memory (so anonymous visitors don't share history).

    Returns the reply plus which tools were used - the UI shows those,
    which makes it obvious the answers come from your algorithms and not
    from the model's imagination.
    """
    history = get_history(user_id, session_key)
    executor = build_agent(user_id, display_name=display_name, verbose=verbose)

    if AGENT_API == "v1":
        # LangGraph agents take and return a flat message list.
        result = executor.invoke(
            {"messages": history + [HumanMessage(content=message)]}
        )
        messages = result.get("messages", [])
        reply = messages[-1].content if messages else ""
        # Tool calls are recorded on the AI messages produced this turn.
        tools_used = []
        for msg in messages[len(history) + 1:]:
            for call in getattr(msg, "tool_calls", None) or []:
                name = call.get("name") if isinstance(call, dict) else getattr(call, "name", None)
                if name and name not in tools_used:
                    tools_used.append(name)
    else:
        result = executor.invoke({"input": message, "chat_history": history})
        reply = result.get("output", "")
        tools_used = []
        for step in result.get("intermediate_steps", []):
            name = getattr(step[0], "tool", None)
            if name and name not in tools_used:
                tools_used.append(name)

    # Some providers return content as a list of parts rather than a string.
    if isinstance(reply, list):
        reply = " ".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in reply
        ).strip()

    history.append(HumanMessage(content=message))
    history.append(AIMessage(content=reply))
    del history[:-MAX_HISTORY_MESSAGES]  # keep only the most recent turns

    return {"reply": reply, "tools_used": tools_used}


if __name__ == "__main__":
    # Quick terminal test:  python chatbot.py
    print("TripTunes Assistant - type 'quit' to exit, 'clear' to reset.\n")
    while True:
        try:
            text = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not text:
            continue
        if text.lower() in ("quit", "exit"):
            break
        if text.lower() == "clear":
            clear_history(None)
            print("(history cleared)\n")
            continue
        try:
            out = chat(text, user_id=None, verbose=True)
        except LLMNotConfigured as exc:
            print(f"\nSetup needed: {exc}\n")
            break
        used = f"  [tools: {', '.join(out['tools_used'])}]" if out["tools_used"] else ""
        print(f"\nAssistant: {out['reply']}{used}\n")
