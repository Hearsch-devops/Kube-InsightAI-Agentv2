
from fastapi import HTTPException

from app.auth import require_roles


class MockUser:
    def __init__(self, role):
        self.role = role


def test_admin_role():
    checker = require_roles("admin")
    user = MockUser("admin")
    assert checker(user) is user
    print("PASS: Admin accepted for admin-only operation")


def test_approver_role():
    checker = require_roles("approver", "admin")
    user = MockUser("approver")
    assert checker(user) is user
    print("PASS: Approver accepted for approval operation")


def test_user_cannot_approve():
    checker = require_roles("approver", "admin")
    user = MockUser("user")

    try:
        checker(user)
    except HTTPException as exc:
        assert exc.status_code == 403
        print("PASS: Regular user denied approval permission")
    else:
        raise AssertionError("Regular user should not be allowed to approve")


def test_invalid_role_configuration():
    try:
        require_roles("superuser")
    except ValueError:
        print("PASS: Invalid role configuration rejected")
    else:
        raise AssertionError("Invalid role configuration should fail")


if __name__ == "__main__":
    test_admin_role()
    test_approver_role()
    test_user_cannot_approve()
    test_invalid_role_configuration()
    print("\nAll RBAC utility tests passed!")
