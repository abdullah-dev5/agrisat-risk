"""Apply pending Supabase migrations (004+) without re-running full schema."""

from __future__ import annotations

import os
import socket
import sys
from pathlib import Path
from urllib.parse import quote, urlparse, urlunparse

ROOT = Path(__file__).resolve().parents[1]
PENDING = [
    ROOT / "supabase" / "migrations" / "004_matiari_pilot_district.sql",
    ROOT / "supabase" / "migrations" / "005_baseline_per_tier.sql",
    ROOT / "supabase" / "migrations" / "006_field_processing_status.sql",
]

POOLER_REGIONS = (
    "ap-south-1",
    "ap-southeast-1",
    "ap-southeast-2",
    "ap-northeast-1",
    "ap-northeast-2",
    "ap-east-1",
    "me-south-1",
    "me-central-1",
    "eu-central-1",
    "eu-west-1",
    "eu-west-2",
    "eu-west-3",
    "us-east-1",
    "us-east-2",
    "us-west-1",
    "us-west-2",
    "ca-central-1",
    "sa-east-1",
)


def _with_sslmode(url: str) -> str:
    parsed = urlparse(url)
    if parsed.query:
        return url
    sep = "&" if parsed.query else "?"
    return f"{url}{sep}sslmode=require"


def _connect_candidates(url: str) -> list[str]:
    parsed = urlparse(url)
    if not parsed.hostname or not parsed.password:
        return [url]

    host = parsed.hostname
    project_ref = host.removeprefix("db.").split(".")[0]
    ipv6_candidates: list[str] = []
    pooler_candidates: list[str] = []

    try:
        infos = socket.getaddrinfo(host, parsed.port or 5432, proto=socket.IPPROTO_TCP)
        for info in infos:
            addr = info[4][0]
            if ":" in addr and not addr.startswith("["):
                netloc = f"{parsed.username}:{quote(parsed.password, safe='')}@[{addr}]:{parsed.port or 5432}"
                ipv6_candidates.append(_with_sslmode(urlunparse(parsed._replace(netloc=netloc))))
    except OSError:
        pass

    for prefix in ("aws-0", "aws-1"):
        for region in POOLER_REGIONS:
            for port in (5432, 6543):
                netloc = (
                    f"postgres.{project_ref}:{quote(parsed.password, safe='')}"
                    f"@{prefix}-{region}.pooler.supabase.com:{port}"
                )
                pooler_candidates.append(_with_sslmode(urlunparse(parsed._replace(netloc=netloc))))

    candidates = ipv6_candidates + [_with_sslmode(url)] + pooler_candidates

    seen: set[str] = set()
    unique: list[str] = []
    for item in candidates:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def _connect(url: str):
    import psycopg2

    return psycopg2.connect(url, connect_timeout=12)


def main() -> int:
    try:
        import psycopg2  # noqa: F401
    except ImportError:
        print("Install: pip install psycopg2-binary")
        return 1

    from dotenv import load_dotenv

    load_dotenv(ROOT / "backend" / ".env")
    url = os.getenv("DATABASE_URL", "").strip()
    if not url or "YOUR_PASSWORD" in url:
        print("Set DATABASE_URL in backend/.env")
        return 1

    print("Connecting to Supabase Postgres...")
    conn = None
    last_error: Exception | None = None
    for candidate in _connect_candidates(url):
        try:
            conn = _connect(candidate)
            host_hint = urlparse(candidate).hostname or "database"
            print(f"Connected via {host_hint}")
            break
        except Exception as exc:
            last_error = exc

    if conn is None:
        print(f"FAILED: {last_error}")
        return 1

    conn.autocommit = True

    try:
        with conn.cursor() as cur:
            for path in PENDING:
                sql = path.read_text(encoding="utf-8")
                print(f"Applying {path.name}...")
                try:
                    cur.execute(sql)
                    print("  OK")
                except Exception as exc:
                    msg = str(exc).lower()
                    if "already exists" in msg or "duplicate" in msg:
                        print("  OK (already applied)")
                    else:
                        print(f"  WARN: {exc}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
