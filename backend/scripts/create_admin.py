"""Securely provision the first IntelliStock administrator."""
from __future__ import annotations

import argparse
import getpass
import os
import re
import sys

from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password, normalize_email
from app.database import SessionLocal
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository


def _required(value: str | None, prompt: str, *, secret: bool = False) -> str:
    if value:
        return value
    return getpass.getpass(prompt) if secret else input(prompt).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Create the initial IntelliStock administrator")
    parser.add_argument("--email", default=os.getenv("INITIAL_ADMIN_EMAIL"))
    parser.add_argument("--username", default=os.getenv("INITIAL_ADMIN_USERNAME"))
    args = parser.parse_args()

    email = normalize_email(_required(args.email, "Administrator email: "))
    username = _required(args.username, "Administrator username: ").strip()
    password_from_env = os.getenv("INITIAL_ADMIN_PASSWORD")
    password = _required(password_from_env, "Administrator password: ", secret=True)
    confirmation = password if password_from_env else _required(None, "Confirm administrator password: ", secret=True)

    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        print("Invalid administrator email.", file=sys.stderr)
        return 2
    if len(username) < 3 or len(username) > 255:
        print("Username must contain between 3 and 255 characters.", file=sys.stderr)
        return 2
    if len(password) < 12:
        print("Password must contain at least 12 characters.", file=sys.stderr)
        return 2
    if password != confirmation:
        print("Passwords do not match.", file=sys.stderr)
        return 2

    with SessionLocal() as db:
        repository = UserRepository(db)
        if repository.get_by_email(email) or repository.get_by_username(username):
            print("A user with that email or username already exists.", file=sys.stderr)
            return 1
        try:
            user = repository.add(
                User(
                    email=email,
                    username=username,
                    hashed_password=hash_password(password),
                    role=UserRole.ADMIN,
                    is_active=True,
                )
            )
        except IntegrityError:
            db.rollback()
            print("Administrator could not be created because the identity already exists.", file=sys.stderr)
            return 1

    print(f"Administrator created successfully (user id: {user.id}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
