"""
Database models for the SDLC Agent Hub.

All tables are INDEX/REGISTRY tables — they never replace the markdown
files as the source of truth. The markdown files govern agent behaviour;
the DB enables fast querying, history, and relationship traversal.
"""
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class Agent(Base):
    __tablename__ = "agents"

    id           = Column(Integer, primary_key=True, index=True)
    name         = Column(String, unique=True, index=True, nullable=False)
    role         = Column(String, nullable=False)
    file_path    = Column(String, nullable=False)
    version      = Column(String, nullable=False, default="1.0.0")
    content_hash = Column(String, nullable=False)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    updated_at   = Column(DateTime(timezone=True), server_default=func.now(),
                          onupdate=func.now())

    executions = relationship("Execution", back_populates="agent")


class Project(Base):
    """One SDLC workspace. Owns workspace/project_{id}/documents/ on disk."""
    __tablename__ = "projects"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    artifacts     = relationship("Artifact",    back_populates="project")
    executions    = relationship("Execution",   back_populates="project")
    pipeline_runs = relationship("PipelineRun", back_populates="project")


class Artifact(Base):
    """Canonical SDLC document for a project. Upserted per (project_id, artifact_type)."""
    __tablename__ = "artifacts"

    id               = Column(Integer, primary_key=True, index=True)
    project_id       = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    artifact_type    = Column(String, nullable=False, index=True)
    file_path        = Column(String, nullable=False)
    markdown_content = Column(Text, nullable=False)
    created_by_agent = Column(String, nullable=False)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    updated_at       = Column(DateTime(timezone=True), server_default=func.now(),
                              onupdate=func.now())

    project = relationship("Project", back_populates="artifacts")


class Execution(Base):
    """Audit log of every agent run — success and failure alike."""
    __tablename__ = "executions"

    id         = Column(Integer, primary_key=True, index=True)
    agent_id   = Column(Integer, ForeignKey("agents.id"),    nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"),  nullable=False, index=True)
    input      = Column(Text, nullable=False)
    output     = Column(Text, nullable=True)
    status     = Column(String, nullable=False, default="success")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    agent   = relationship("Agent",   back_populates="executions")
    project = relationship("Project", back_populates="executions")


class PipelineRun(Base):
    """
    One full automated SDLC pipeline execution.

    workflow_name:      name of the workflow file used (None = PIPELINE_STAGES default)
    review_iterations:  number of Reviewer→Coder loops completed in this run
    status:             running | completed | failed
    """
    __tablename__ = "pipeline_runs"

    id                = Column(Integer, primary_key=True, index=True)
    project_id        = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    idea              = Column(Text, nullable=False)
    workflow_name     = Column(String, nullable=True)   # null = used PIPELINE_STAGES default
    status            = Column(String, nullable=False, default="running")
    review_iterations = Column(Integer, nullable=False, default=0)
    started_at        = Column(DateTime(timezone=True), server_default=func.now())
    completed_at      = Column(DateTime(timezone=True), nullable=True)

    project = relationship("Project", back_populates="pipeline_runs")
    steps   = relationship("PipelineStep", back_populates="run",
                           order_by="PipelineStep.sequence")


class PipelineStep(Base):
    """
    One agent execution within a PipelineRun.

    sequence:      position within the run (re-used step numbers occur during review loops)
    iteration:     review loop iteration number (0 = first pass, 1 = first re-run, etc.)
    status:        running | success | failed | skipped
    """
    __tablename__ = "pipeline_steps"

    id            = Column(Integer, primary_key=True, index=True)
    run_id        = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=False, index=True)
    sequence      = Column(Integer, nullable=False)
    iteration     = Column(Integer, nullable=False, default=0)
    agent_name    = Column(String, nullable=False)
    artifact_type = Column(String, nullable=True)
    status        = Column(String, nullable=False, default="running")
    duration_ms   = Column(Integer, nullable=True)
    error         = Column(Text, nullable=True)
    started_at    = Column(DateTime(timezone=True), server_default=func.now())
    completed_at  = Column(DateTime(timezone=True), nullable=True)

    run = relationship("PipelineRun", back_populates="steps")
