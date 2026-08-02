"""
Find a working Gemini model for this key.

Run:  python test_key.py

Lists the models your key can use, then actually calls each candidate
until one succeeds, and prints the winner. Also writes the full model
list to models.txt so nothing scrolls away.
"""

import os

key = os.environ.get("GOOGLE_API_KEY", "")
print("GOOGLE_API_KEY set:", bool(key), f"(len {len(key)})" if key else "(EMPTY)")
if not key:
    print('-> Set it first:  $env:GOOGLE_API_KEY = "AIza..."')
    raise SystemExit(1)

# --- List every model this key can use for chat ---
candidates = []
try:
    import google.generativeai as genai
    genai.configure(api_key=key)
    usable = [
        m.name.replace("models/", "")
        for m in genai.list_models()
        if "generateContent" in getattr(m, "supported_generation_methods", [])
    ]
    with open("models.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(usable))
    print(f"\n{len(usable)} chat-capable models (full list saved to models.txt).")

    # Prefer cheap/fast 'flash' models, newest-looking first, skip previews.
    flash = [m for m in usable if "flash" in m and "preview" not in m and "exp" not in m]
    pro = [m for m in usable if "pro" in m and "preview" not in m and "exp" not in m]
    candidates = sorted(flash, reverse=True) + sorted(pro, reverse=True)
    # fall back to anything at all if the tidy filter caught nothing
    candidates = candidates or usable
except Exception as exc:
    print("\nCouldn't list models:", type(exc).__name__, "-", exc)
    # sensible guesses if listing failed
    candidates = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-flash-latest"]

# --- Try each candidate until one actually answers ---
from langchain_google_genai import ChatGoogleGenerativeAI

print("\nTrying models until one works:\n")
winner = None
for model in candidates[:8]:
    try:
        llm = ChatGoogleGenerativeAI(model=model, temperature=0)
        reply = llm.invoke("Say hello in three words.").content
        print(f"  [OK]   {model}  ->  {reply!r}")
        winner = model
        break
    except Exception as exc:
        msg = str(exc).split("\n")[0][:90]
        print(f"  [fail] {model}  ->  {msg}")

if winner:
    print(f"\n=====================================")
    print(f"  USE THIS MODEL:  {winner}")
    print(f"=====================================")
    print("Tell Claude this name and it'll set it as the default.")
else:
    print("\nNo model worked. Likely the free tier isn't provisioned on this")
    print("project. Options: enable billing in AI Studio, or switch the app to")
    print("Groq/Ollama (both free) - ask Claude to help.")
