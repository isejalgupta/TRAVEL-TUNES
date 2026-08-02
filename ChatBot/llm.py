"""
LLM provider layer for TripTunes.

One job: hand back a LangChain chat model. Which model you actually get
is decided by an environment variable, so the rest of the app never
knows or cares who the provider is.

    TRIPTUNES_LLM_PROVIDER = gemini | groq | ollama | openai

Why a factory instead of importing ChatGoogleGenerativeAI everywhere:
free tiers change, rate limits change, and you may want to demo this
offline. Swapping providers should be a one-line env change, not a
refactor. Every model returned here speaks the same LangChain
interface, so chatbot.py is written once and runs against any of them.

Setup (pick one):

  gemini  - free tier, get a key at https://aistudio.google.com/apikey
            pip install langchain-google-genai
            set GOOGLE_API_KEY

  groq    - free tier, very fast, https://console.groq.com/keys
            pip install langchain-groq
            set GROQ_API_KEY

  ollama  - fully local, no key, no rate limit, works offline.
            install from https://ollama.com then: ollama pull llama3.1
            pip install langchain-ollama

  openai  - paid, https://platform.openai.com
            pip install langchain-openai
            set OPENAI_API_KEY
"""

import os

DEFAULT_PROVIDER = "gemini"

# Sensible default model per provider. Override with TRIPTUNES_LLM_MODEL.
DEFAULT_MODELS = {
    "gemini": "gemini-flash-lite-latest",
    "groq": "llama-3.3-70b-versatile",
    "ollama": "llama3.1",
    "openai": "gpt-4o-mini",
}

# Which pip package and which env var each provider needs. Used only to
# produce a helpful error message instead of a raw ImportError.
REQUIREMENTS = {
    "gemini": ("langchain-google-genai", "GOOGLE_API_KEY"),
    "groq": ("langchain-groq", "GROQ_API_KEY"),
    "ollama": ("langchain-ollama", None),  # local, no key needed
    "openai": ("langchain-openai", "OPENAI_API_KEY"),
}


class LLMNotConfigured(RuntimeError):
    """Raised when the chosen provider is missing its package or API key.

    The chat API catches this and turns it into a clean 503 with setup
    instructions, rather than letting the whole app crash on startup.
    """


def get_provider() -> str:
    return os.environ.get("TRIPTUNES_LLM_PROVIDER", DEFAULT_PROVIDER).strip().lower()


def get_model_name(provider: str | None = None) -> str:
    provider = provider or get_provider()
    return os.environ.get("TRIPTUNES_LLM_MODEL", DEFAULT_MODELS.get(provider, ""))


def _require_key(provider: str):
    """Check the API key is present before we try to build the client."""
    package, env_var = REQUIREMENTS[provider]
    if env_var and not os.environ.get(env_var):
        raise LLMNotConfigured(
            f"{provider} needs the {env_var} environment variable. "
            f"Get a key, then run:  set {env_var}=your-key-here  (Windows)  "
            f"or  export {env_var}=your-key-here  (Mac/Linux). "
            f"See AI_SETUP.md."
        )


def build_llm(temperature: float = 0.3):
    """Return a LangChain chat model for the configured provider.

    temperature: 0 = deterministic and factual, 1 = creative. We keep it
    lowish because this agent reports real numbers from the database and
    we don't want it inventing prices.
    """
    provider = get_provider()

    if provider not in REQUIREMENTS:
        raise LLMNotConfigured(
            f"Unknown provider '{provider}'. "
            f"Choose one of: {', '.join(REQUIREMENTS)}."
        )

    _require_key(provider)
    model = get_model_name(provider)
    package = REQUIREMENTS[provider][0]

    try:
        if provider == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(model=model, temperature=temperature)

        if provider == "groq":
            from langchain_groq import ChatGroq
            return ChatGroq(model=model, temperature=temperature)

        if provider == "ollama":
            from langchain_ollama import ChatOllama
            return ChatOllama(
                model=model,
                temperature=temperature,
                base_url=os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
            )

        if provider == "openai":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model=model, temperature=temperature)

    except ImportError as exc:
        raise LLMNotConfigured(
            f"Provider '{provider}' needs a package that isn't installed. "
            f"Run:  pip install {package}"
        ) from exc


def describe() -> dict:
    """Small status payload so the UI can show which model is in use
    and whether it's actually ready, without sending a real message."""
    provider = get_provider()
    package, env_var = REQUIREMENTS.get(provider, ("unknown", None))
    ready = True
    reason = ""
    try:
        build_llm()
    except LLMNotConfigured as exc:
        ready = False
        reason = str(exc)
    except Exception as exc:  # network/client errors shouldn't 500 the status route
        ready = False
        reason = f"{type(exc).__name__}: {exc}"

    return {
        "provider": provider,
        "model": get_model_name(provider),
        "ready": ready,
        "reason": reason,
    }
