"""
SDLC Agent Hub — FastAPI application entrypoint.

Startup sequence:
  1. Create all DB tables (idempotent)
  2. Sync agents/ directory → agents registry table
  3. Log available skills, workflows, and templates (file-only, no DB sync needed)
"""
from fastapi import FastAPI

from app.api.routes import agents as agents_routes
from app.api.routes import executions as executions_routes
from app.api.routes import pipeline as pipeline_routes
from app.api.routes import projects as projects_routes
from app.db.database import SessionLocal, init_db
from app.services.agent_loader import sync_agents_from_disk
from app.services.llm_client import active_model, active_provider
from app.services.skill_loader import list_skills
from app.services.template_loader import list_templates
from app.services.workflow_loader import list_workflows

app = FastAPI(
    title="AI SDLC Agent Hub",
    description=(
        "Backend for storing and dynamically executing SDLC agents "
        "(PM → Architect → Developer → Coder → Reviewer → Tester) "
        "defined as markdown files. Supports Groq and Anthropic LLMs."
    ),
    version="1.0.0",
)

app.include_router(agents_routes.router)
app.include_router(executions_routes.router)
app.include_router(projects_routes.router)
app.include_router(pipeline_routes.router)


@app.on_event("startup")
def on_startup():
    init_db()

    db = SessionLocal()
    try:
        synced_agents = sync_agents_from_disk(db)
        print(f"[startup] Agents  : {len(synced_agents)} synced from agents/")
    finally:
        db.close()

    skills = list_skills()
    print(f"[startup] Skills  : {len(skills)} available — "
          f"{', '.join(s['name'] for s in skills)}")

    workflows = list_workflows()
    print(f"[startup] Workflows: {len(workflows)} available — "
          f"{', '.join(w['name'] for w in workflows)}")

    templates = list_templates()
    print(f"[startup] Templates: {len(templates)} available — "
          f"{', '.join(t['name'] for t in templates)}")

    print(f"[startup] LLM     : provider={active_provider()}  model={active_model()}")


@app.get("/health")
def health():
    return {
        "status":   "ok",
        "provider": active_provider(),
        "model":    active_model(),
    }
