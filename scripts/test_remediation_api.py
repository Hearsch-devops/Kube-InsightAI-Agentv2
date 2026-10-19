
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from app.api.routes import persist_remediation_proposal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.auth import get_db
from app.database import (
    Base,
    User,
    RemediationProposal,
    ApprovalDecision,
    AuditEvent,
)
from app.auth import hash_password, create_access_token


class RemediationAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.temp_dir.name) / "remediation_test.db"
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
            db.query(ApprovalDecision).delete()
            db.query(RemediationProposal).delete()
            db.query(User).delete()

            self.admin = User(
                username="testadmin",
                password_hash=hash_password("Admin-Test-Password-123!"),
                role="admin",
                is_active=True,
            )
            self.approver = User(
                username="testapprover",
                password_hash=hash_password("Approver-Test-Password-123!"),
                role="approver",
                is_active=True,
            )
            self.readonly = User(
                username="testreadonly",
                password_hash=hash_password("Readonly-Test-Password-123!"),
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

            proposal = RemediationProposal(
                action="restart_deployment",
                namespace="testing-files",
                deployment="scenario-3-crashloopbackoff",
                reason="Test proposal only",
                status="proposed",
                execution_enabled=False,
                requested_by="testuser",
            )
            db.add(proposal)
            db.commit()
            db.refresh(proposal)
            self.proposal_id = proposal.id

    def headers(self, token):
        return {"Authorization": f"Bearer {token}"}

    def test_approver_can_approve_without_enabling_execution(self):
        response = self.client.post(
            f"/api/remediation/proposals/{self.proposal_id}/approve",
            headers=self.headers(self.approver_token),
            json={"comment": "Approved for testing only"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "approved")
        self.assertFalse(response.json()["execution_enabled"])

        with self.TestSession() as db:
            proposal = db.get(RemediationProposal, self.proposal_id)
            decisions = db.scalars(select(ApprovalDecision)).all()
            events = db.scalars(select(AuditEvent)).all()

            self.assertEqual(proposal.status, "approved")
            self.assertFalse(proposal.execution_enabled)
            self.assertEqual(len(decisions), 1)
            self.assertEqual(decisions[0].decision, "approve")
            self.assertTrue(
                any(event.event_type == "proposal_approved" for event in events)
            )

    def test_admin_can_reject(self):
        response = self.client.post(
            f"/api/remediation/proposals/{self.proposal_id}/reject",
            headers=self.headers(self.admin_token),
            json={"comment": "Rejected for testing"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "rejected")
        self.assertFalse(response.json()["execution_enabled"])

        with self.TestSession() as db:
            events = db.scalars(select(AuditEvent)).all()
            self.assertTrue(
                any(event.event_type == "proposal_rejected" for event in events)
            )

    def test_readonly_user_cannot_approve_or_reject(self):
        for action in ("approve", "reject"):
            response = self.client.post(
                f"/api/remediation/proposals/{self.proposal_id}/{action}",
                headers=self.headers(self.readonly_token),
                json={},
            )
            self.assertEqual(response.status_code, 403, response.text)

    def test_unauthenticated_user_cannot_approve(self):
        response = self.client.post(
            f"/api/remediation/proposals/{self.proposal_id}/approve",
            json={},
        )
        self.assertEqual(response.status_code, 401, response.text)

    def test_unknown_proposal_returns_404(self):
        response = self.client.post(
            "/api/remediation/proposals/999999/approve",
            headers=self.headers(self.admin_token),
            json={},
        )
        self.assertEqual(response.status_code, 404, response.text)

    def test_proposal_cannot_be_decided_twice(self):
        first = self.client.post(
            f"/api/remediation/proposals/{self.proposal_id}/approve",
            headers=self.headers(self.approver_token),
            json={},
        )
        self.assertEqual(first.status_code, 200, first.text)

        second = self.client.post(
            f"/api/remediation/proposals/{self.proposal_id}/reject",
            headers=self.headers(self.admin_token),
            json={},
        )
        self.assertEqual(second.status_code, 409, second.text)

        with self.TestSession() as db:
            decisions = db.scalars(select(ApprovalDecision)).all()
            self.assertEqual(len(decisions), 1)

    def test_list_proposals_requires_authentication(self):
        response = self.client.get("/api/remediation/proposals")
        self.assertEqual(response.status_code, 401, response.text)

    def test_approver_can_list_proposals(self):
        response = self.client.get(
            "/api/remediation/proposals",
            headers=self.headers(self.approver_token),
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(
            any(item["id"] == self.proposal_id for item in response.json())
        )

    def test_readonly_user_sees_only_own_proposals(self):
        with self.TestSession() as db:
            own_proposal = RemediationProposal(
                action="restart_deployment",
                namespace="testing-files",
                deployment="scenario-2-imagepullbackoff",
                reason="Owned by readonly user",
                status="proposed",
                execution_enabled=False,
                requested_by="testreadonly",
            )
            db.add(own_proposal)
            db.commit()
            db.refresh(own_proposal)
            own_id = own_proposal.id

        response = self.client.get(
            "/api/remediation/proposals",
            headers=self.headers(self.readonly_token),
        )

        self.assertEqual(response.status_code, 200, response.text)
        ids = {item["id"] for item in response.json()}
        self.assertIn(own_id, ids)
        self.assertNotIn(self.proposal_id, ids)

    def test_readonly_user_cannot_view_another_users_proposal(self):
        response = self.client.get(
            f"/api/remediation/proposals/{self.proposal_id}",
            headers=self.headers(self.readonly_token),
        )

        self.assertEqual(response.status_code, 404, response.text)

    def test_admin_can_view_another_users_proposal(self):
        response = self.client.get(
            f"/api/remediation/proposals/{self.proposal_id}",
            headers=self.headers(self.admin_token),
        )

        self.assertEqual(response.status_code, 200, response.text)

    def test_readonly_user_cannot_create_proposal_via_chat(self):
        graph_result = {
            "answer": "A restart proposal is ready.",
            "route": "remediation",
            "remediation_proposal": {
                "action": "restart_deployment",
                "status": "proposed",
                "deployment": "scenario-3-crashloopbackoff",
                "namespace": "testing-files",
                "reason": "Test proposal only",
                "execution_enabled": False,
            },
        }

        with patch(
            "app.api.routes.graph.ainvoke",
            new_callable=AsyncMock,
            return_value=graph_result,
        ):
            response = self.client.post(
                "/api/chat",
                headers=self.headers(self.readonly_token),
                json={
                    "message": (
                        "Restart deployment scenario-3-crashloopbackoff "
                        "in namespace testing-files"
                    )
                },
            )

        self.assertEqual(response.status_code, 403, response.text)

        with self.TestSession() as db:
            proposals = db.scalars(
                select(RemediationProposal).where(
                    RemediationProposal.requested_by == "testreadonly"
                )
            ).all()
            self.assertEqual(len(proposals), 0)

    def test_admin_can_create_proposal_via_chat(self):
        graph_result = {
            "answer": "A restart proposal is ready.",
            "route": "remediation",
            "remediation_proposal": {
                "action": "restart_deployment",
                "status": "proposed",
                "deployment": "scenario-3-crashloopbackoff",
                "namespace": "testing-files",
                "reason": "Test proposal only",
                "execution_enabled": False,
            },
        }

        def persist_to_test_db(proposal, requested_by):
            proposal = {
                **proposal,
                "execution_enabled": False,
            }
            with self.TestSession() as db:
                record = RemediationProposal(
                    action=proposal["action"],
                    namespace=proposal["namespace"],
                    deployment=proposal["deployment"],
                    reason=proposal["reason"],
                    status="proposed",
                    execution_enabled=False,
                    requested_by=requested_by,
                )
                db.add(record)
                db.flush()
                proposal["id"] = record.id
                db.add(
                    AuditEvent(
                        proposal_id=record.id,
                        actor=requested_by,
                        event_type="proposal_created",
                        details={
                            "action": record.action,
                            "namespace": record.namespace,
                            "deployment": record.deployment,
                            "execution_enabled": False,
                        },
                    )
                )
                db.commit()
                return proposal

        with (
            patch(
                "app.api.routes.graph.ainvoke",
                new_callable=AsyncMock,
                return_value=graph_result,
            ),
            patch(
                "app.api.routes.persist_remediation_proposal",
                side_effect=persist_to_test_db,
            ),
        ):
            response = self.client.post(
                "/api/chat",
                headers=self.headers(self.admin_token),
                json={
                    "message": (
                        "Restart deployment scenario-3-crashloopbackoff "
                        "in namespace testing-files"
                    )
                },
            )

        self.assertEqual(response.status_code, 200, response.text)
        proposal = response.json()["remediation_proposal"]
        with self.TestSession() as db:
            saved_proposal = db.scalar(
                select(RemediationProposal).where(
                    RemediationProposal.requested_by == "testadmin"
                )
            )

            self.assertIsNotNone(saved_proposal)
            self.assertEqual(saved_proposal.requested_by, "testadmin")
            self.assertFalse(saved_proposal.execution_enabled)
        self.assertFalse(proposal["execution_enabled"])

        with self.TestSession() as db:
            record = db.get(RemediationProposal, proposal["id"])
            self.assertIsNotNone(record)
            self.assertEqual(record.requested_by, "testadmin")
            self.assertFalse(record.execution_enabled)
            events = db.scalars(
                select(AuditEvent).where(
                    AuditEvent.proposal_id == proposal["id"]
                )
            ).all()
            self.assertTrue(
                any(event.event_type == "proposal_created" for event in events)
            )

    def test_approver_can_create_proposal_via_chat(self):
        from unittest.mock import AsyncMock, patch

        mock_result = {
            "answer": "A restart proposal has been prepared for review.",
            "route": "remediation",
            "remediation_proposal": {
                "action": "restart_deployment",
                "status": "proposed",
                "deployment": "scenario-3-crashloopbackoff",
                "namespace": "testing-files",
                "reason": "Test proposal only",
                "execution_enabled": False,
            },
        }

        def persist_to_test_db(proposal, requested_by):
            with self.TestSession() as db:
                saved = RemediationProposal(
                    action=proposal["action"],
                    namespace=proposal["namespace"],
                    deployment=proposal["deployment"],
                    reason=proposal["reason"],
                    status="proposed",
                    execution_enabled=False,
                    requested_by=requested_by,
                )

                db.add(saved)
                db.flush()  # Generates saved.id

                db.add(
                    AuditEvent(
                        proposal_id=saved.id,  # Important: link to this proposal
                        actor=requested_by,
                        event_type="proposal_created",
                        details={
                            "action": saved.action,
                            "namespace": saved.namespace,
                            "deployment": saved.deployment,
                            "execution_enabled": False,
                        },
                    )
                )

                db.commit()
                db.refresh(saved)

                return {
                    **proposal,
                    "id": saved.id,
                    "requested_by": requested_by,
                    "execution_enabled": False,
                }

        with (
            patch(
                "app.api.routes.graph.ainvoke",
                new_callable=AsyncMock,
                return_value=mock_result,
            ),
            patch(
                "app.api.routes.persist_remediation_proposal",
                side_effect=persist_to_test_db,
            ),
        ):
            response = self.client.post(
                "/api/chat",
                headers=self.headers(self.approver_token),
                json={
                    "message": (
                        "Restart deployment scenario-3-crashloopbackoff "
                        "in namespace testing-files"
                    )
                },
            )

        self.assertEqual(response.status_code, 200, response.text)

        proposal = response.json()["remediation_proposal"]
        self.assertEqual(proposal["requested_by"], "testapprover")
        self.assertFalse(proposal["execution_enabled"])

        with self.TestSession() as db:
            saved = db.scalar(
                select(RemediationProposal).where(
                    RemediationProposal.id == proposal["id"]
                )
            )
            self.assertIsNotNone(saved)
            self.assertEqual(saved.requested_by, "testapprover")
            self.assertEqual(saved.status, "proposed")
            self.assertFalse(saved.execution_enabled)

            audit = db.scalar(
                select(AuditEvent).where(
                    AuditEvent.proposal_id == saved.id,
                    AuditEvent.event_type == "proposal_created",
                )
            )
            all_audits = db.scalars(select(AuditEvent)).all()

            self.assertIsNotNone(audit)

    def test_readonly_user_cannot_create_proposal_via_chat(self):
        from unittest.mock import AsyncMock, patch

        graph_result = {
            "answer": "A restart proposal has been prepared.",
            "route": "remediation",
            "remediation_proposal": {
                "action": "restart_deployment",
                "status": "proposed",
                "deployment": "scenario-3-crashloopbackoff",
                "namespace": "testing-files",
                "reason": "Test proposal only",
                "execution_enabled": False,
            },
        }

        with patch(
            "app.api.routes.graph.ainvoke",
            new_callable=AsyncMock,
            return_value=graph_result,
        ):
            response = self.client.post(
                "/api/chat",
                headers=self.headers(self.readonly_token),
                json={
                    "message": (
                        "Restart deployment scenario-3-crashloopbackoff "
                        "in namespace testing-files"
                    )
                },
            )

        self.assertEqual(response.status_code, 403, response.text)

        with self.TestSession() as db:
            created = db.scalar(
                select(RemediationProposal).where(
                    RemediationProposal.requested_by == "testreadonly"
                )
            )
            self.assertIsNone(created)
        
    def test_readonly_user_can_use_chat_for_diagnostics(self):
        from unittest.mock import AsyncMock, patch

        graph_result = {
            "answer": "Deployment scenario-3-crashloopbackoff is unhealthy.",
            "route": "mcp",
            "remediation_proposal": None,
        }

        with patch(
            "app.api.routes.graph.ainvoke",
            new_callable=AsyncMock,
            return_value=graph_result,
        ):
            response = self.client.post(
                "/api/chat",
                headers=self.headers(self.readonly_token),
                json={
                    "message": (
                        "Why is deployment scenario-3-crashloopbackoff "
                        "unhealthy in namespace testing-files?"
                    )
                },
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("unhealthy", response.json()["response"].lower())

if __name__ == "__main__":
    unittest.main(verbosity=2)
