
import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    create_engine,
    text,
    UniqueConstraint
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


# Store the database outside the application source directory.
DEFAULT_DATABASE_PATH = Path(__file__).resolve().parent.parent / "data" / "kube_insightai.db"

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{DEFAULT_DATABASE_PATH}",
)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("username", name="uq_users_username"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False, default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

class RemediationProposal(Base):
    __tablename__ = "remediation_proposals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    namespace: Mapped[str] = mapped_column(String(63), nullable=False)

    # Retain the legacy non-null database column for compatibility.
    # Pod proposals will store an empty string in this field.
    deployment: Mapped[str] = mapped_column(
        String(253), nullable=False, default=""
    )

    # Generic target fields support multiple Kubernetes resource types.
    resource_kind: Mapped[str] = mapped_column(
        String(63), nullable=False, default="Deployment"
    )
    resource_name: Mapped[str] = mapped_column(
        String(253), nullable=False, default=""
    )

    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="proposed"
    )
    execution_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    requested_by: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

class ApprovalDecision(Base):
    __tablename__ = "approval_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    proposal_id: Mapped[int] = mapped_column(
        ForeignKey("remediation_proposals.id"), nullable=False, index=True
    )
    decided_by: Mapped[str] = mapped_column(String(255), nullable=False)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    proposal_id: Mapped[int | None] = mapped_column(
        ForeignKey("remediation_proposals.id"), nullable=True, index=True
    )
    actor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

class InvestigationHistory(Base):
    __tablename__ = "investigation_history"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    route: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    namespace: Mapped[str | None] = mapped_column(
        String(63), nullable=True
    )
    sources: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

def init_db() -> None:
    """Create tables and safely migrate existing remediation proposals."""
    if DATABASE_URL.startswith("sqlite:///"):
        database_path = DATABASE_URL.removeprefix("sqlite:///")

        if database_path != ":memory:":
            Path(database_path).expanduser().resolve().parent.mkdir(
                parents=True, exist_ok=True
            )

    # Create tables that do not yet exist.
    Base.metadata.create_all(bind=engine)

    # SQLite create_all() does not add columns to existing tables.
    if engine.dialect.name == "sqlite":
        with engine.begin() as connection:
            columns = {
                row[1]
                for row in connection.execute(
                    text("PRAGMA table_info(remediation_proposals)")
                )
            }

            if not columns:
                return

            if "resource_kind" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE remediation_proposals "
                        "ADD COLUMN resource_kind VARCHAR(63) "
                        "NOT NULL DEFAULT 'Deployment'"
                    )
                )

            if "resource_name" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE remediation_proposals "
                        "ADD COLUMN resource_name VARCHAR(253) "
                        "NOT NULL DEFAULT ''"
                    )
                )

            # Backfill generic targets for historical Deployment proposals.
            connection.execute(
                text(
                    "UPDATE remediation_proposals "
                    "SET resource_kind = 'Deployment', "
                    "resource_name = deployment "
                    "WHERE resource_name = '' AND deployment IS NOT NULL"
                )
            )

