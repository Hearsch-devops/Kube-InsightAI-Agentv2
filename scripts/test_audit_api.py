
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.auth import get_db, create_access_token, hash_password
from app.database import (
    Base,
    User,
    AuditEvent,
)


class AuditAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Reuse the isolated test database pattern from test_admin_api.py.
        import tempfile
        from pathlib import Path
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.temp_dir.name) / "audit_test.db"
        cls.engine = create_engine(
            f"sqlite:///{cls.db_path}",
            connect_args={"check_same_thread": False},
        )
        cls.TestSession = sessionmaker(
            bind=cls.engine,
            autoflush=False,
            autocommit=False,
        )
        Base.metadata.create_all(bind=cls.engine)

        def override_get_db():
            db = cls.TestSession()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        cls.client.close()
        cls.engine.dispose()
        cls.temp_dir.cleanup()

    def setUp(self):
        with self.TestSession() as db:
            db.query(AuditEvent).delete()
            db.query(User).delete()

            self.admin = User(
                username="auditadmin",
                password_hash=hash_password("Audit-Admin-Password-123!"),
                role="admin",
                is_active=True,
            )
            self.approver = User(
                username="auditapprover",
                password_hash=hash_password("Audit-Approver-Password-123!"),
                role="approver",
                is_active=True,
            )
            self.readonly = User(
                username="auditreadonly",
                password_hash=hash_password("Audit-Readonly-Password-123!"),
                role="user",
                is_active=True,
            )

            db.add_all([self.admin, self.approver, self.readonly])
            db.commit()

            db.refresh(self.admin)
            db.refresh(self.approver)
            db.refresh(self.readonly)

            self.admin_token = create_access_token(self.admin)
            self.approver_token = create_access_token(self.approver)
            self.readonly_token = create_access_token(self.readonly)

            db.add_all([
                AuditEvent(
                    actor="auditadmin",
                    event_type="proposal_created",
                    details={"namespace": "testing-files"},
                ),
                AuditEvent(
                    actor="auditapprover",
                    event_type="proposal_approved",
                    details={"execution_enabled": False},
                ),
                AuditEvent(
                    actor="auditadmin",
                    event_type="proposal_rejected",
                    details={"reason": "test"},
                ),
            ])
            db.commit()

    def headers(self, token):
        return {"Authorization": f"Bearer {token}"}

    def test_admin_can_list_audit_events(self):
        response = self.client.get(
            "/api/admin/audit",
            headers=self.headers(self.admin_token),
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(response.json()["items"]), 3)

    def test_approver_can_list_audit_events(self):
        response = self.client.get(
            "/api/admin/audit",
            headers=self.headers(self.approver_token),
        )
        self.assertEqual(response.status_code, 200, response.text)

    def test_readonly_user_is_forbidden(self):
        response = self.client.get(
            "/api/admin/audit",
            headers=self.headers(self.readonly_token),
        )
        self.assertEqual(response.status_code, 403, response.text)

    def test_unauthenticated_request_is_rejected(self):
        response = self.client.get("/api/admin/audit")
        self.assertEqual(response.status_code, 401, response.text)

    def test_pagination_limits_results(self):
        response = self.client.get(
            "/api/admin/audit?limit=2&offset=0",
            headers=self.headers(self.admin_token),
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(response.json()["items"]), 2)
        self.assertEqual(response.json()["limit"], 2)
        self.assertEqual(response.json()["offset"], 0)

    def test_audit_events_include_expected_fields(self):
        response = self.client.get(
            "/api/admin/audit",
            headers=self.headers(self.admin_token),
        )
        self.assertEqual(response.status_code, 200, response.text)

        event = response.json()["items"][0]
        self.assertIn("actor", event)
        self.assertIn("event_type", event)
        self.assertIn("created_at", event)
        self.assertIn("details", event)


if __name__ == "__main__":
    unittest.main(verbosity=2)
