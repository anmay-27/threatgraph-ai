"""Explicit local account administration. Never silently claim historical evidence."""

import argparse, sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(root / "backend"), str(root)]
from sqlalchemy import select
from app.models.database import Session
from app.services.auth import Account

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("email")
    parser.add_argument("--role", required=True, choices=["USER", "ANALYST", "ADMIN"])
    args = parser.parse_args()
    with Session() as db:
        user = db.scalar(select(Account).where(Account.email == args.email.lower()))
        if not user:
            raise SystemExit("Register the account first.")
        user.role = args.role
        db.commit()
    print("Role updated. Sign out and sign in again.")
