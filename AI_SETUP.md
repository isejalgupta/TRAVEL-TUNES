# TripTunes AI Assistant — Setup

The assistant is a **LangChain tool-calling agent**. The language model
supplies the conversation; every fact it states comes from your existing
TripTunes code (Dijkstra, the knapsack optimiser, the backtracking
scheduler, the trie, KMP search, and the trips database).

---

## 1. Install

```bash
pip install -r requirements.txt
```

## 2. Get a free API key (Google Gemini — the default)

1. Go to <https://aistudio.google.com/apikey>
2. Sign in with a Google account and click **Create API key**
3. Set it as an environment variable:

**Windows (PowerShell)**
```powershell
$env:GOOGLE_API_KEY = "your-key-here"
```

**Windows (Command Prompt)**
```cmd
set GOOGLE_API_KEY=your-key-here
```

**Mac / Linux**
```bash
export GOOGLE_API_KEY="your-key-here"
```

> Set in the *same terminal* you run the app from. To make it permanent on
> Windows: search "Edit the system environment variables" → Environment
> Variables → New.

## 3. Run

```bash
python app.py
```

Open <http://127.0.0.1:8000> and tap the **AI** tab.

---

## Switching providers

Nothing in the app code changes — only environment variables.

| Provider | Cost | Env vars | Install |
|---|---|---|---|
| **Gemini** (default) | Free tier | `GOOGLE_API_KEY` | `pip install langchain-google-genai` |
| **Groq** | Free tier, very fast | `TRIPTUNES_LLM_PROVIDER=groq`, `GROQ_API_KEY` | `pip install langchain-groq` |
| **Ollama** | Free forever, offline | `TRIPTUNES_LLM_PROVIDER=ollama` | `pip install langchain-ollama` |
| **OpenAI** | Paid | `TRIPTUNES_LLM_PROVIDER=openai`, `OPENAI_API_KEY` | `pip install langchain-openai` |

Override the model with `TRIPTUNES_LLM_MODEL`. The default is
`gemini-flash-lite-latest`, which is what the free tier reliably serves.
If you ever get a `RESOURCE_EXHAUSTED` / `limit: 0` error, a different
model is being gated — run `python test_key.py` to find one your key can
actually use, then set `TRIPTUNES_LLM_MODEL` to its name.

### Ollama — no key, no limits, works offline

Useful if a free tier changes, or for demoing without internet:

1. Install from <https://ollama.com>
2. `ollama pull llama3.1`
3. `set TRIPTUNES_LLM_PROVIDER=ollama`

Runs entirely on your machine. Needs roughly 8 GB RAM and replies more
slowly than the hosted options.

---

## Testing without the web app

```bash
python chatbot.py
```

A terminal chat with `verbose=True`, so you can watch the agent decide
which tool to call — useful for a demo or a viva.

---

## How it fits together

```
index.html  (AI tab)
    |  POST /api/chat
chat_api.py     - HTTP layer, optional JWT auth
    |
chatbot.py      - system prompt, agent loop, per-user memory
    |
    +-- llm.py         - returns a chat model (Gemini/Groq/Ollama/OpenAI)
    |
    +-- chat_tools.py  - 12 tools the model can call
             |
             +-- activities.py   knapsack, backtracking, quicksort
             +-- graph.py        Dijkstra (via citiesdata.load_graph)
             +-- music.py        trie, KMP, playlist generation
             +-- database.py     trips, activities, songs
```

**The agent loop:** your message plus the tool descriptions go to the
model → the model either answers or requests a tool call → `AgentExecutor`
runs that Python function → the result goes back to the model → repeat
until it can answer. That reason → act → observe cycle is what makes this
an *agent* rather than a fixed chain; it chooses which tools to run at
runtime, and often chains three or four in a single reply.

### The twelve tools

| Tool | Backed by |
|---|---|
| `list_destinations` | activities table |
| `find_activities` | quicksort + filters |
| `plan_within_budget` | 0/1 knapsack DP |
| `plan_day_schedule` | backtracking search |
| `find_route` | Dijkstra's algorithm |
| `search_songs` | KMP substring search |
| `list_music_options` | songs table |
| `build_playlist` | filter + rating sort |
| `get_my_trips` | trips table (per-user) |
| `get_trip_details` | trips table (per-user) |
| `create_trip` | writes a trip + days |
| `add_activity_to_trip` | writes a trip activity |

---

## Things to try

- "What can I do in Agra?"
- "Plan a day in Jaipur, 6 hours and 300 rupees"
- "Cheapest way from Delhi to Goa" *(routes through Mumbai — real Dijkstra)*
- "Now make me a playlist for that drive"
- "Save that as a trip called Goa Getaway" *(login required)*

---

## Notes

- **Privacy:** the trip tools close over the logged-in user's id, so one
  user's agent physically cannot read another's trips.
- **No hallucinated data:** the system prompt forbids inventing
  activities, prices or routes, and each reply shows which tools ran.
- **Memory** is in-process, so it resets when the server restarts.
  Persisting it with a LangGraph checkpointer is the natural next step.
- **Logged out** still works for routes, activities and music — only
  saving trips needs an account.

## Troubleshooting

| Problem | Fix |
|---|---|
| Amber "AI not configured" banner | API key not set in *this* terminal — re-set it and restart |
| `LLMNotConfigured: needs a package` | `pip install langchain-google-genai` |
| 502 "AI service failed" | Usually a free-tier rate limit — wait a minute |
| Assistant says it can't save trips | Log in on the Trip tab first |
| Ollama connection refused | Ollama isn't running — start it, then `ollama pull llama3.1` |
