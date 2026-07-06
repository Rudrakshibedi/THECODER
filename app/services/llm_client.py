"""
Groq LLM Client

Environment Variables
---------------------
GROQ_API_KEY      Required
GROQ_MODEL        Optional (default: llama-3.3-70b-versatile)
LLM_MAX_TOKENS    Optional (default: 4096; per-agent overrides in
                  app.core.config.AGENT_MAX_TOKENS_MAP take precedence)

Usage:
    from app.services.llm_client import generate

    response = generate(system_prompt, user_prompt)
"""

import os
from typing import Optional

from dotenv import load_dotenv
from groq import Groq

from app.core.config import DEFAULT_LLM_MAX_TOKENS
from app.utils.token_guard import trim_messages

# Load environment variables from .env
load_dotenv()

# Retained for backwards compatibility (e.g. anything importing this name
# directly); DEFAULT_LLM_MAX_TOKENS in app.core.config is now the single
# source of truth and already reads the same LLM_MAX_TOKENS env var.
LLM_MAX_TOKENS = DEFAULT_LLM_MAX_TOKENS
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


class LLMExecutionError(RuntimeError):
    """Raised when a Groq API request fails."""


_client = None


def _get_client() -> Groq:
    """Create the Groq client once and reuse it."""
    global _client

    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise LLMExecutionError(
                "GROQ_API_KEY not found. Please add it to your .env file."
            )

        _client = Groq(api_key=api_key)

    return _client


def generate(
    system_prompt: str,
    user_prompt: str,
    max_tokens: Optional[int] = None,
) -> str:
    """
    Generate a response from Groq.

    `max_tokens`, if given, overrides the global LLM_MAX_TOKENS default for
    this single call. Callers (agent_runner) use this to apply per-agent
    completion-length budgets (AGENT_MAX_TOKENS_MAP) sized to what each
    agent actually produces, instead of one flat ceiling for every agent.
    """
    try:
        client = _get_client()

        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ]

        # Token guard: every request is capped in message count and
        # per-role message size before it reaches Groq, regardless of how
        # large the caller-supplied prompts were. This is a backstop, not
        # the primary trimming mechanism — see app/utils/token_guard.py.
        safe_messages = trim_messages(messages)

        response = client.chat.completions.create(
            model=GROQ_MODEL,
            max_tokens=max_tokens or LLM_MAX_TOKENS,
            messages=safe_messages,
        )

        if not response.choices:
            raise LLMExecutionError("Groq returned no choices.")

        text = response.choices[0].message.content

        if not text:
            raise LLMExecutionError("Groq returned an empty response.")

        return text.strip()

    except LLMExecutionError:
        raise

    except Exception as exc:
        raise LLMExecutionError(f"Groq API call failed: {exc}") from exc


def active_provider() -> str:
    """Return the active provider."""
    return "groq"


def active_model() -> str:
    """Return the active Groq model."""
    return GROQ_MODEL