from __future__ import annotations

import argparse
from getpass import getpass

from fitmind_agent.db.session import SessionLocal
from fitmind_agent.repositories.auth import UserRepository
from fitmind_agent.services.auth_service import AuthService


def main() -> None:
    parser = argparse.ArgumentParser(description="Safely set a FitMind user's password.")
    parser.add_argument("identifier", help="Existing username or email")
    args = parser.parse_args()

    password = getpass("New password: ")
    if len(password) < 8 or len(password) > 128:
        raise SystemExit("Password must contain 8-128 characters.")
    if password != getpass("Confirm password: "):
        raise SystemExit("Passwords do not match.")

    with SessionLocal() as db:
        user = UserRepository(db).get_by_identifier(args.identifier)
        if user is None:
            raise SystemExit("User not found.")
        user.password_hash = AuthService(db).hash_password(password)
        user.auth_version += 1
        db.commit()
        print(f"Password updated for user {user.username} (id={user.id}).")


if __name__ == "__main__":
    main()
