
import os
import sqlite3
import subprocess
import sys


def test_legacy_database_migration(tmp_path):
    db_path = tmp_path / "legacy.db"

    # Simulate the original schema, before generic resource fields existed.
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE remediation_proposals (
                id INTEGER PRIMARY KEY,
                action VARCHAR(100) NOT NULL,
                namespace VARCHAR(63) NOT NULL,
                deployment VARCHAR(253) NOT NULL,
                reason TEXT NOT NULL,
                status VARCHAR(30) NOT NULL DEFAULT 'proposed',
                execution_enabled BOOLEAN NOT NULL DEFAULT 0,
                requested_by VARCHAR(255),
                created_at DATETIME NOT NULL
            );

            INSERT INTO remediation_proposals (
                id, action, namespace, deployment, reason,
                status, execution_enabled, created_at
            ) VALUES (
                1, 'restart_deployment', 'kube-insightaiv2',
                'kube-insightaiv2-agent', 'Legacy proposal',
                'proposed', 0, '2026-10-19 00:00:00'
            );
            """
        )

    # Import the application with DATABASE_URL pointed at this temporary DB.
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path}"

    script = """
from sqlalchemy import inspect, text
from app.database import engine, init_db

init_db()

with engine.connect() as connection:
    columns = {column["name"]: column for column in inspect(engine).get_columns("remediation_proposals")}
    assert "resource_kind" in columns
    assert "resource_name" in columns
    assert columns["deployment"]["nullable"] is False

    row = connection.execute(
        text(
            "SELECT deployment, resource_kind, resource_name "
            "FROM remediation_proposals WHERE id = 1"
        )
    ).one()

    assert row.deployment == "kube-insightaiv2-agent"
    assert row.resource_kind == "Deployment"
    assert row.resource_name == "kube-insightaiv2-agent"

init_db()
print("Legacy migration and idempotency passed")
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        env=env,
        capture_output=True,
        text=True,
        cwd=os.getcwd(),
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Legacy migration and idempotency passed" in result.stdout
