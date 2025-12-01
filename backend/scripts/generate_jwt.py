"""Utility to mint a JWT with a tenant_id claim for local testing.

Example:
    python backend/scripts/generate_jwt.py --tenant-id 123e4567-e89b-12d3-a456-426614174000 --secret changeme
"""

import argparse
import uuid
from datetime import datetime, timedelta

from jose import jwt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a JWT containing a tenant_id claim.")
    parser.add_argument("--tenant-id", help="UUID for tenant_id; generates one if omitted.")
    parser.add_argument("--secret", default="changeme", help="JWT signing secret (default: changeme).")
    parser.add_argument("--alg", default="HS256", help="JWT algorithm (default: HS256).")
    parser.add_argument("--ttl-seconds", type=int, default=3600, help="Token TTL in seconds (default: 3600).")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    tenant_id = args.tenant_id or str(uuid.uuid4())

    payload = {"tenant_id": tenant_id}
    if args.ttl_seconds:
        payload["exp"] = datetime.utcnow() + timedelta(seconds=args.ttl_seconds)

    token = jwt.encode(payload, args.secret, algorithm=args.alg)

    print(f"tenant_id: {tenant_id}")
    print(f"token: {token}")


if __name__ == "__main__":
    main()
