
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_login_and_current_user():
    response = client.post(
        "/api/auth/login",
        json={
            "username": "admin",
            "password": input("Enter the admin password: "),
        },
    )

    assert response.status_code == 200, response.text

    token = response.json()["access_token"]
    assert response.json()["token_type"] == "bearer"

    me = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert me.status_code == 200, me.text
    assert me.json()["username"] == "admin"
    assert me.json()["role"] == "admin"

    print("Login successful; authenticated identity verified.")


if __name__ == "__main__":
    test_login_and_current_user()
