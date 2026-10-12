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
    assert "CREATE TABLE teacher_assignments" in result.stdout
    assert "ADD COLUMN role VARCHAR(20) DEFAULT 'student' NOT NULL" in result.stdout
    assert "NOT (is_published AND is_archived)" in result.stdout
    assert "revision > 0" in result.stdout
    assert "CREATE TABLE enrollments" in result.stdout
    assert "CREATE TABLE access_requests" in result.stdout
    assert "CREATE TABLE access_grants" in result.stdout
    assert "CREATE UNIQUE INDEX uq_access_requests_pending" in result.stdout
    assert "expires_at > created_at" in result.stdout
