
from fastapi.testclient import TestClient

from app.auth import create_access_token
from app.database import SessionLocal, User
from app.main import app

client = TestClient(app)


def test_wrong_password():
    response = client.post(
        "/api/auth/login",
        json={
            "username": "admin",
            "password": "Definitely-Wrong-Password-123!",
        },
    )
    assert response.status_code == 401, response.text
    print("PASS: Incorrect password rejected")


def test_missing_token():
    response = client.get("/api/auth/me")
    assert response.status_code == 401, response.text
    print("PASS: Missing token rejected")


def test_invalid_token():
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid.token.value"},
    )
    assert response.status_code == 401, response.text
    print("PASS: Invalid token rejected")


def test_valid_admin_token():
    with SessionLocal() as db:
        admin = (
            db.query(User)
            .filter(User.username == "admin")
            .first()
        )

        assert admin is not None, "Admin account not found"
        assert admin.is_active, "Admin account is inactive"

        token = create_access_token(admin)

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["username"] == "admin"
    assert data["role"] == "admin"

    print("PASS: Valid admin token accepted")


if __name__ == "__main__":
    test_wrong_password()
    test_missing_token()
    test_invalid_token()
    test_valid_admin_token()
    print("\nAll authentication security tests passed!")
