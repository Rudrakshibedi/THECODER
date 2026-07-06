"""
Central configuration for the SDLC Agent Hub.
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
AGENTS_DIR    = BASE_DIR / "agents"
WORKFLOWS_DIR = BASE_DIR / "workflows"
SKILLS_DIR    = BASE_DIR / "skills"
TEMPLATES_DIR = BASE_DIR / "templates"
WORKSPACE_DIR = BASE_DIR / "workspace"
DATABASE_URL  = f"sqlite:///{BASE_DIR / 'agent_hub.db'}"

# Ensure all content directories exist on import
for _d in (AGENTS_DIR, WORKFLOWS_DIR, SKILLS_DIR, TEMPLATES_DIR, WORKSPACE_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ── Agent → artifact mapping ───────────────────────────────────────────────────
# (artifact_type, filename) — single source of truth for what each agent writes.
AGENT_ARTIFACT_MAP = {
    "product-manager": ("requirements",       "requirements.md"),
    "architect":       ("solution-design",    "solution-design.md"),
    "developer":       ("implementation-plan","implementation-plan.md"),
    "coder":           ("source-code",        "source-code.md"),
    "reviewer":        ("review-report",      "review-report.md"),
    "tester":          ("test-strategy",      "test-strategy.md"),
    # tester also writes qa-report.md — handled separately in pipeline_service
    # because one agent produces two artifacts
}

# ── Upstream artifact dependencies ────────────────────────────────────────────
# Checked before every LLM call. Fails fast (no cost) if upstream is missing.
AGENT_DEPENDENCY_MAP = {
    "architect": [
        "requirements",
    ],

    "developer": [
        "requirements",
        "solution-design",
    ],

    "coder": [
        "requirements",
        "solution-design",
        "implementation-plan",
    ],

    "reviewer": [
        "requirements",
        "solution-design",
        "implementation-plan",
        "source-code",
    ],

    "tester": [
        "requirements",
        "solution-design",
        "implementation-plan",
        "source-code",
    ],
}

# ── Skill assignments ──────────────────────────────────────────────────────────
# Skills whose Instructions section is prepended to the agent system prompt.
AGENT_SKILL_MAP = {
    "product-manager": ["requirements-analysis"],
    "architect":       ["system-design"],
    "developer":       ["implementation-planning"],
    "coder":           ["source-code-generation"],
    "reviewer":        ["code-review"],
    "tester":          ["unit-test-generation", "qa-validation"],
}

# ── Template assignments ───────────────────────────────────────────────────────
# Templates whose '## Structure' section is injected as the agent's Required
# Output Format. This is the single source of truth for agent → template
# resolution — agent .md files only carry a `template`/`templates` reference
# in frontmatter; the actual mapping used at runtime lives here, mirroring
# the AGENT_SKILL_MAP pattern above. Tester maps to two templates because it
# produces two distinct artifacts (test-strategy + qa-report).
AGENT_TEMPLATE_MAP = {
    "product-manager": ["requirements-template"],
    "architect":       ["solution-design-template"],
    "developer":       ["implementation-plan-template"],
    "coder":           ["code-template"],
    "reviewer":        ["review-report-template"],
    "tester":          ["test-strategy-template", "qa-report-template"],
}

# ── Artifact explosion ─────────────────────────────────────────────────────────
# Artifact types whose markdown content follows the '### <relative/path>' +
# fenced-code-block convention (defined by code-template.md / the unit-tests
# portion of test-strategy-template.md) and should therefore be exploded into
# real files on disk under workspace/project_{id}/, in addition to the single
# consolidated .md file already written under documents/. This is additive —
# the consolidated markdown artifact is never removed, so existing API/DB
# behaviour is unaffected.
EXPLODE_ARTIFACT_TYPES = {"source-code", "unit-tests"}

# ── Default pipeline stages ────────────────────────────────────────────────────
# Used by pipeline_service when no workflow_name is provided.
# Format: (sequence, agent_name)
PIPELINE_STAGES = [
    (1, "product-manager"),
    (2, "architect"),
    (3, "developer"),
    (4, "coder"),
    (5, "reviewer"),
    (6, "tester"),
]

# ── Review-loop settings ───────────────────────────────────────────────────────
# Maximum number of Reviewer → Coder → Reviewer iterations before the
# pipeline gives up and fails the run. Prevents infinite loops.
import os as _os

MAX_REVIEW_ITERATIONS = int(_os.getenv("MAX_REVIEW_ITERATIONS", "3"))

# ── Prompt / context limits ────────────────────────────────────────────────────
# Maximum characters taken from any single upstream artifact when it is
# injected into a downstream agent's prompt (per-artifact cap).
MAX_CONTEXT_CHARS = int(_os.getenv("MAX_CONTEXT_CHARS", "4000"))

# Maximum characters across ALL upstream artifacts combined for a single
# agent call. Some agents depend on several artifacts at once (reviewer
# depends on 4, tester on 4) — without a combined cap, MAX_CONTEXT_CHARS
# is effectively multiplied by the dependency count. When an agent has
# more than one dependency, the per-artifact budget is
# min(MAX_CONTEXT_CHARS, MAX_TOTAL_CONTEXT_CHARS / number_of_dependencies),
# so high-fan-in agents don't blow past the intended total budget.
MAX_TOTAL_CONTEXT_CHARS = int(_os.getenv("MAX_TOTAL_CONTEXT_CHARS", "9000"))

# Floor so a single-dependency slice never gets squeezed into uselessness
# when MAX_TOTAL_CONTEXT_CHARS is set low.
MIN_ARTIFACT_CONTEXT_CHARS = int(_os.getenv("MIN_ARTIFACT_CONTEXT_CHARS", "1500"))

# ── LLM output limits ──────────────────────────────────────────────────────────
# Fallback max_tokens for any agent not listed in AGENT_MAX_TOKENS_MAP.
# Lowered from the previous flat 8192 default — no agent in this pipeline
# produces an artifact anywhere near that size, and an over-large ceiling
# only invites runaway/rambling completions that eat into the daily quota.
DEFAULT_LLM_MAX_TOKENS = int(_os.getenv("LLM_MAX_TOKENS", "4096"))

# Per-agent max_tokens overrides, sized to each agent's typical artifact:
# requirements/solution-design/implementation-plan/review-report are prose
# documents in the 1-3K token range; coder and tester emit fenced source
# code / test files and need materially more headroom.
AGENT_MAX_TOKENS_MAP = {
    "product-manager": int(_os.getenv("MAX_TOKENS_PRODUCT_MANAGER", "3000")),
    "architect":        int(_os.getenv("MAX_TOKENS_ARCHITECT", "3000")),
    "developer":        int(_os.getenv("MAX_TOKENS_DEVELOPER", "3000")),
    "coder":            int(_os.getenv("MAX_TOKENS_CODER", "6000")),
    "reviewer":         int(_os.getenv("MAX_TOKENS_REVIEWER", "3000")),
    "tester":           int(_os.getenv("MAX_TOKENS_TESTER", "6000")),
}
