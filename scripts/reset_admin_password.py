"""Local recovery helper, sent into an existing backend container without rebuilding it."""

import argparse
import sys
import warnings
from getpass import GetPassWarning, getpass

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models import User, UserRole


def reset_super_admin_password(session: Session, student_no: str, password: str) -> str:
    if not 8 <= len(password) <= 16:
        raise ValueError("The password must contain 8-16 characters.")
    user = session.scalar(
        select(User).where(User.student_no == student_no.strip(), User.role == UserRole.SUPER_ADMIN)
    )
    if user is None:
        raise ValueError("Super-admin account not found. No account was created or changed.")
    user.password_hash = hash_password(password)
    session.commit()
    return user.student_no


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reset an existing super-admin password")
    parser.add_argument("student_no", nargs="?", default="admin")
    args = parser.parse_args(argv)
    try:
        with warnings.catch_warnings():
            # Refuse getpass's echoing fallback when no interactive terminal is available.
            warnings.simplefilter("error", GetPassWarning)
            password = getpass("New password (8-16 characters): ")
            confirmation = getpass("Confirm password: ")
        if password != confirmation:
            raise ValueError("The two passwords do not match. No changes were saved.")
        from app.db.session import SessionLocal

        with SessionLocal() as session:
            student_no = reset_super_admin_password(session, args.student_no, password)
    except (EOFError, KeyboardInterrupt, GetPassWarning):
        print(
            "Password reset cancelled. Run this script in an interactive terminal.", file=sys.stderr
        )
        return 1
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except SQLAlchemyError:
        print("Database operation failed. Check the backend before retrying.", file=sys.stderr)
        return 1
    print(f"Password updated for super-admin: {student_no}. Sign in with your new password.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
