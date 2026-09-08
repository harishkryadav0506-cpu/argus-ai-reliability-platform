"""
ARGUS Database Models (Section 22)

Phase 1 scope: define the schema so migrations + health checks work.
Later phases (3-8) will populate these tables from real agent activity —
do not fabricate rows anywhere in the codebase.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String, default="unknown")   # low|medium|high|critical
    status: Mapped[str] = mapped_column(String, default="open")        # open|investigating|resolved
    failure_type: Mapped[str] = mapped_column(String, default="UNKNOWN")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    metrics: Mapped[list["MetricSnapshot"]] = relationship(back_populates="incident")
    diagnoses: Mapped[list["Diagnosis"]] = relationship(back_populates="incident")
    recovery_actions: Mapped[list["RecoveryAction"]] = relationship(back_populates="incident")
    evaluations: Mapped[list["Evaluation"]] = relationship(back_populates="incident")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="incident")


class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"))
    metric_name: Mapped[str] = mapped_column(String)
    value: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    incident: Mapped["Incident"] = relationship(back_populates="metrics")


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"))
    root_cause: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    evidence: Mapped[str] = mapped_column(Text, default="")   # JSON-encoded evidence list
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    incident: Mapped["Incident"] = relationship(back_populates="diagnoses")


class RecoveryAction(Base):
    __tablename__ = "recovery_actions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"))
    strategy: Mapped[str] = mapped_column(String)
    risk: Mapped[str] = mapped_column(String, default="unknown")           # low|medium|high
    approval_status: Mapped[str] = mapped_column(String, default="not_required")  # not_required|pending|approved|rejected
    execution_status: Mapped[str] = mapped_column(String, default="pending")      # pending|executed|failed
    result: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    incident: Mapped["Incident"] = relationship(back_populates="recovery_actions")


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"))
    metric: Mapped[str] = mapped_column(String)
    score: Mapped[float] = mapped_column(Float)
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    incident: Mapped["Incident"] = relationship(back_populates="evaluations")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    incident_id: Mapped[str | None] = mapped_column(ForeignKey("incidents.id"), nullable=True)
    actor: Mapped[str] = mapped_column(String)          # "system" | "agent:<name>" | "user:<id>"
    action: Mapped[str] = mapped_column(String)
    result: Mapped[str] = mapped_column(String, default="")
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    incident: Mapped["Incident | None"] = relationship(back_populates="audit_logs")
