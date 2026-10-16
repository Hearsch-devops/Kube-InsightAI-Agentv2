import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.auth import get_db, create_access_token, hash_password
from app.database import Base, User


class AdminAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.temp_dir.name) / "test_admin.db"

        cls.engine = create_engine(
            f"sqlite:///{cls.db_path}",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.TestSession = sessionmaker(
            bind=cls.engine,
            autoflush=False,
            expire_on_commit=False,
        )

        Base.metadata.create_all(bind=cls.engine)

        with cls.TestSession() as db:
            admin = User(
                username="testadmin",
                password_hash=hash_password("Admin-Test-Password-123!"),
                role="admin",
                is_active=True,
            )
            approver = User(
                username="testapprover",
                password_hash=hash_password("Approver-Test-Password-123!"),
                role="approver",
                is_active=True,
            )
            reader = User(
                username="testreader",
                password_hash=hash_password("Reader-Test-Password-123!"),
                role="user",
                is_active=True,
            )
            db.add_all([admin, approver, reader])
            db.commit()

            cls.admin_id = admin.id
            cls.approver_id = approver.id
            cls.reader_id = reader.id

        def override_get_db():
            db = cls.TestSession()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

        with cls.TestSession() as db:
            cls.admin_token = create_access_token(
                db.get(User, cls.admin_id)
            )
            cls.approver_token = create_access_token(
                db.get(User, cls.approver_id)
            )
            cls.reader_token = create_access_token(
                db.get(User, cls.reader_id)
            )

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=cls.engine)
        cls.engine.dispose()
        cls.temp_dir.cleanup()

    def headers(self, token):
        return {"Authorization": f"Bearer {token}"}

    def test_admin_can_create_user(self):
        response = self.client.post(
            "/api/admin/users",
            headers=self.headers(self.admin_token),
            json={
                "username": "newapprover",
                "password": "New-Approver-Password-123!",
                "role": "approver",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        data = response.json()
        self.assertEqual(data["username"], "newapprover")
        self.assertEqual(data["role"], "approver")
        self.assertNotIn("password_hash", data)

        with self.TestSession() as db:
            user = db.scalar(
                select(User).where(User.username == "newapprover")
            )
            self.assertIsNotNone(user)
            self.assertNotEqual(
                user.password_hash, "New-Approver-Password-123!"
            )

    def test_admin_can_list_users(self):
        response = self.client.get(
            "/api/admin/users",
            headers=self.headers(self.admin_token),
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("testadmin", [u["username"] for u in response.json()])
        self.assertTrue(
            all("password_hash" not in u for u in response.json())
        )

    def test_duplicate_username_rejected(self):
        response = self.client.post(
            "/api/admin/users",
            headers=self.headers(self.admin_token),
            json={
                "username": "testreader",
                "password": "Another-Password-123!",
                "role": "user",
            },
        )
        self.assertEqual(response.status_code, 409, response.text)

    def test_non_admin_cannot_manage_users(self):
        for role, token in (
            ("approver", self.approver_token),
            ("user", self.reader_token),
        ):
            with self.subTest(role=role):
                response = self.client.get(
                    "/api/admin/users",
                    headers=self.headers(token),
                )
                self.assertEqual(
                    response.status_code,
                    403,
                    f"{role} should not manage users: {response.text}",
                )

    def test_admin_can_change_role(self):
        response = self.client.patch(
            f"/api/admin/users/{self.reader_id}/role",
            headers=self.headers(self.admin_token),
            json={"role": "approver"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["role"], "approver")

    def test_admin_can_deactivate_user(self):
        # Use a dedicated account so other tests remain independent.
        with self.TestSession() as db:
            reader = User(
                username="deactivation_target",
                password_hash=hash_password(
                    "Deactivation-Test-Password-123!"
                ),
                role="user",
                is_active=True,
            )
            db.add(reader)
            db.commit()
            reader_id = reader.id

        try:
            response = self.client.patch(
                f"/api/admin/users/{reader_id}/status",
                headers=self.headers(self.admin_token),
                json={"is_active": False},
            )
            self.assertEqual(response.status_code, 200, response.text)
            self.assertFalse(response.json()["is_active"])
        finally:
            with self.TestSession() as db:
                reader = db.get(User, reader_id)
                if reader is not None:
                    db.delete(reader)
                    db.commit()

    def test_last_active_admin_cannot_be_demoted(self):
        response = self.client.patch(
            f"/api/admin/users/{self.admin_id}/role",
            headers=self.headers(self.admin_token),
            json={"role": "user"},
        )
        self.assertEqual(response.status_code, 409, response.text)

    def test_last_active_admin_cannot_be_deactivated(self):
        response = self.client.patch(
            f"/api/admin/users/{self.admin_id}/status",
            headers=self.headers(self.admin_token),
            json={"is_active": False},
        )
        self.assertEqual(response.status_code, 409, response.text)

    def test_admin_cannot_deactivate_self(self):
        # Create a second admin so last-admin protection doesn't mask this test.
        with self.TestSession() as db:
            second_admin = User(
                username="secondadmin",
                password_hash=hash_password("Second-Admin-Password-123!"),
                role="admin",
                is_active=True,
            )
            db.add(second_admin)
            db.commit()
            second_admin_id = second_admin.id

        response = self.client.patch(
            f"/api/admin/users/{self.admin_id}/status",
            headers=self.headers(self.admin_token),
            json={"is_active": False},
        )
        self.assertEqual(response.status_code, 409, response.text)

        with self.TestSession() as db:
            db.delete(db.get(User, second_admin_id))
            db.commit()


if __name__ == "__main__":
    unittest.main(verbosity=2)
