"""
Token Guard

A minimal, reusable safety layer that caps the size of message payloads
sent to the LLM provider (Groq). This exists to prevent 429 "rate limit
exceeded" errors caused by unbounded prompt growth (long message history
and/or oversized message content).

This module is intentionally dependency-free and side-effect-free so it
can sit in front of ANY LLM call site (chat-style message lists today,
and any future multi-turn/agent-to-agent history) without requiring
changes to business logic, prompts, or agent behaviour.

IMPORTANT — role-aware limits:
  The previous implementation applied one flat `max_chars` limit (3000)
  to every message, including the `system` message. In this pipeline the
  system message carries the agent's identity, skills, and — critically —
  the "## Required Output Format" block copied from the template layer.
  That block is always appended *last* by prompt_builder, so a flat
  ~3000 char cap silently amputated it for every agent whose system
  prompt exceeds that size (reviewer ~7.3K chars, coder ~5.9K chars,
  tester ~7.5K chars all did). The model then had no instructions on the
  required output shape, which hurt output quality without saving any
  *useful* tokens — the system prompt is bounded, structural content; it
  is not where runaway token growth comes from. Upstream artifact content
  is, and that is already trimmed in agent_runner.py.

  This module now applies separate, configurable limits per role:
    - `system` is capped generously (default 16,000 chars) — high enough
      to never truncate a normal agent+skills+template prompt, but still
      an absolute backstop against a pathological agent/template file.
    - `user` is capped at a smaller, configurable default — this is the
      last line of defense behind the per-artifact trimming already done
      in agent_runner.py (MAX_CONTEXT_CHARS) and the total-context budget
      (MAX_TOTAL_CONTEXT_CHARS). It should rarely trigger in practice.

  All limits are overridable via environment variables so they can be
  tuned per-deployment without a code change.

Usage:
    from app.utils.token_guard import trim_messages

    safe_messages = trim_messages(messages)
    response = client.chat.completions.create(messages=safe_messages, ...)
"""
import os
from typing import Dict, List, Union

DEFAULT_MAX_MESSAGES = int(os.getenv("TOKEN_GUARD_MAX_MESSAGES", "6"))

# Per-role character ceilings. `system` is intentionally large — it is a
# backstop, not the trimming mechanism (see module docstring above).
ROLE_MAX_CHARS = {
    "system": int(os.getenv("TOKEN_GUARD_MAX_SYSTEM_CHARS", "16000")),
    "user": int(os.getenv("TOKEN_GUARD_MAX_USER_CHARS", "9000")),
    "assistant": int(os.getenv("TOKEN_GUARD_MAX_ASSISTANT_CHARS", "9000")),
}
DEFAULT_MAX_CHARS = int(os.getenv("TOKEN_GUARD_MAX_CHARS", "9000"))

_TRUNCATION_MARKER = "\n\n...(truncated to reduce prompt size)...\n\n"


def truncate_smart(content: str, max_chars: int) -> str:
    """Truncate `content` to at most `max_chars`, keeping both the head and
    the tail of the text rather than just the head.

    Rationale: artifacts and reports in this pipeline often put the most
    load-bearing information at the *end* (e.g. a review report's final
    "**Verdict**:" line, a QA report's summary), while the head carries
    structural/section context. A naive head-only cut (the previous
    behaviour) reliably threw away exactly the part a downstream agent
    most needed. This keeps ~70% head / ~30% tail, which preserves both.
    """
    if max_chars <= 0 or len(content) <= max_chars:
        return content

    if max_chars <= len(_TRUNCATION_MARKER) + 40:
        # Not enough budget for a head+tail split — fall back to a plain
        # head cut so we never return something longer than requested.
        return content[:max_chars]

    budget = max_chars - len(_TRUNCATION_MARKER)
    head_len = int(budget * 0.7)
    tail_len = budget - head_len
    return content[:head_len] + _TRUNCATION_MARKER + content[-tail_len:]


def trim_messages(
    messages: List[Dict],
    max_messages: int = DEFAULT_MAX_MESSAGES,
    max_chars: Union[int, Dict[str, int], None] = None,
) -> List[Dict]:
    """Return a token-safe copy of `messages`.

    Guarantees:
      - At most `max_messages` messages are kept (the most recent ones —
        i.e. the last `max_messages` entries of the input list). In this
        codebase every LLM call is a single-shot [system, user] pair with
        no growing chat history, so this rarely does anything today — it
        exists as a guard for any future multi-turn use of this function.
      - Each message's `content` is truncated per-role (see ROLE_MAX_CHARS)
        using `truncate_smart` so both the head and tail are preserved.
      - The input list/dicts are never mutated; a new list of new dicts
        is returned.
      - Non-string `content` (e.g. None) is passed through unchanged
        aside from message-count capping.

    `max_chars` may be a single int (applied to every role, preserving the
    old call signature), a dict overriding specific roles, or omitted to
    use the role-aware defaults in ROLE_MAX_CHARS.
    """
    if not messages:
        return []

    if isinstance(max_chars, int):
        limits = {"system": max_chars, "user": max_chars, "assistant": max_chars}
    elif isinstance(max_chars, dict):
        limits = {**ROLE_MAX_CHARS, **max_chars}
    else:
        limits = ROLE_MAX_CHARS

    # Keep only the most recent `max_messages` messages.
    capped = messages[-max_messages:] if max_messages > 0 else list(messages)

    safe_messages: List[Dict] = []
    for message in capped:
        new_message = dict(message)
        content = new_message.get("content")
        role = new_message.get("role", "user")
        limit = limits.get(role, DEFAULT_MAX_CHARS)

        if isinstance(content, str) and len(content) > limit:
            new_message["content"] = truncate_smart(content, limit)

        safe_messages.append(new_message)

    return safe_messages
