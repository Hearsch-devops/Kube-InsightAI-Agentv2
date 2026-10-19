
import os
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import get_db, hash_password
from app.database import Base, User
from app.main import app


def test_login_and_current_user():
    # Use an isolated temporary database for this test.
    temp_dir = tempfile.TemporaryDirectory()
    db_path = Path(temp_dir.name) / "test_auth.db"

    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestSession = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        with TestSession() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db

    try:
        # Create a dedicated test account; never use real admin credentials.
        with TestSession() as db:
            db.add(
                User(
                    username="auth_test_admin",
                    password_hash=hash_password("Test-Only-Password-123!"),
                    role="admin",
                    is_active=True,
                )
            )
            db.commit()

        with TestClient(app) as client:
            response = client.post(
                "/api/auth/login",
                json={
                    "username": "auth_test_admin",
                    "password": "Test-Only-Password-123!",
                },
            )

            assert response.status_code == 200, response.text

            body = response.json()
            token = body["access_token"]
            assert body["token_type"] == "bearer"

            me = client.get(
                "/api/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )

            assert me.status_code == 200, me.text
            assert me.json()["username"] == "auth_test_admin"
            assert me.json()["role"] == "admin"

    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()
        temp_dir.cleanup()
