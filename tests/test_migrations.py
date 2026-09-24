import subprocess
import sys


def test_initial_migration_generates_postgresql_sql() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        check=True,
        text=True,
        capture_output=True,
    )
    assert "CREATE TABLE users" in result.stdout
    assert "CREATE UNIQUE INDEX ix_users_email" in result.stdout
    assert "password_hash" in result.stdout
