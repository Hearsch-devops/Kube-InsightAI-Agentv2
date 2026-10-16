
import getpass
import sys

from sqlalchemy.exc import IntegrityError

from app.auth import hash_password
from app.database import SessionLocal, User, init_db


def main():
    init_db()

    username = input("Admin username: ").strip()

    if not username or len(username) > 100:
        print("Username must contain 1–100 characters.")
        sys.exit(1)

    password = getpass.getpass("Admin password (hidden): ")
    confirm = getpass.getpass("Confirm admin password: ")

    if password != confirm:
        print("Passwords do not match.")
        sys.exit(1)

    if len(password) < 12:
        print("Password must be at least 12 characters.")
        sys.exit(1)

    with SessionLocal() as db:
        existing = (
            db.query(User)
            .filter(User.username == username)
            .first()
        )

        if existing:
            print("Username already exists. No changes made.")
            sys.exit(1)

        admin = User(
            username=username,
            password_hash=hash_password(password),
            role="admin",
            is_active=True,
        )

        try:
            db.add(admin)
            db.commit()
            print(f"Administrator '{username}' created successfully.")
        except IntegrityError:
            db.rollback()
            print("Username already exists. No changes made.")
            sys.exit(1)


if __name__ == "__main__":
    main()
