import argparse
import json
import os
import sys
import subprocess
from pathlib import Path


TEMPLATE_PLAN = """# Project Plan

## TASK_001: Setup authentication
- [ ] Create auth_handler.py with login/logout functions
- [ ] Add JWT token validation helpers
- [ ] Write error handling for invalid credentials
- Depends on:
- Status: PENDING

## TASK_002: Build dashboard UI
- [ ] Create main_window.py with glassmorphic design
- [ ] Implement sidebar navigation with neon accents
- [ ] Add dark theme stylesheet
- Depends on: TASK_001
- Status: PENDING

## TASK_003: Integrate database layer
- [ ] Create db_handler.py with connection pooling
- [ ] Add CRUD operations for user data
- [ ] Write comprehensive exception handling
- Depends on:
- Status: PENDING

## TASK_004: Write tests for auth module
- [ ] Create test_auth_handler.py
- [ ] Cover login/logout flows (positive + negative)
- [ ] Test JWT validation and expiration
- Depends on: TASK_001, TASK_003
- Status: PENDING
"""

TEMPLATE_AUTH = """import json
import os
import time
from typing import Any


TOKEN_EXPIRY_SECONDS = 3600


class AuthenticationError(Exception):
    """Raised when authentication fails."""


def _load_user_database(file_path: str) -> dict[str, dict[str, Any]]:
    """Load user credentials from a JSON file."""
    try:
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        raise AuthenticationError(f"Invalid user database format: {e}")


def login(username: str, password: str, db_path: str | None = None) -> dict[str, Any]:
    """Authenticate a user and return a session token."""
    if not username or not password:
        raise AuthenticationError("Username and password are required")
    db_path = db_path or os.environ.get("AUTH_DB_PATH", "users.json")
    try:
        users = _load_user_database(db_path)
    except AuthenticationError:
        raise
    try:
        user = users.get(username)
    except Exception as e:
        raise AuthenticationError(f"Database access error: {e}")
    if user is None:
        raise AuthenticationError("Invalid username or password")
    token = _generate_token(username)
    return {"token": token, "username": username, "expires_in": TOKEN_EXPIRY_SECONDS}


def logout(token: str, token_store: dict[str, float] | None = None) -> bool:
    """Invalidate a session token."""
    if not token:
        raise AuthenticationError("Token is required for logout")
    store = token_store if token_store is not None else _active_tokens
    try:
        store.pop(token, None)
        return True
    except Exception as e:
        raise AuthenticationError(f"Logout failed: {e}")


def _generate_token(username: str) -> str:
    """Generate a simple session token."""
    raw = f"{username}:{time.time()}:{os.urandom(16).hex()}"
    return raw


def validate_token(token: str, token_store: dict[str, float] | None = None) -> dict[str, Any]:
    """Validate a session token and return user information."""
    if not token:
        raise AuthenticationError("Token is required")
    try:
        store = token_store if token_store is not None else _active_tokens
        expiry = store.get(token)
        if expiry is None:
            raise AuthenticationError("Invalid or expired token")
        if time.time() > expiry:
            store.pop(token, None)
            raise AuthenticationError("Token has expired")
        return {"valid": True, "username": "user", "expires_at": expiry}
    except AuthenticationError:
        raise
    except Exception as e:
        raise AuthenticationError(f"Token validation error: {e}")


_active_tokens: dict[str, float] = {}
"""

TEMPLATE_DB = """import os
import sqlite3
import threading
from collections import OrderedDict
from typing import Any


class DatabaseError(Exception):
    """Raised when a database operation fails."""


class ConnectionPool:
    """A thread-safe SQLite connection pool."""

    def __init__(self, db_path: str, max_connections: int = 5):
        self.db_path = db_path
        self.max_connections = max_connections
        self._pool: OrderedDict[int, sqlite3.Connection] = OrderedDict()
        self._lock = threading.Lock()

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new SQLite connection."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            return conn
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to create connection: {e}")

    def acquire(self) -> sqlite3.Connection:
        """Acquire a connection from the pool."""
        try:
            with self._lock:
                if self._pool:
                    _id, conn = self._pool.popitem(last=False)
                    return conn
            return self._create_connection()
        except Exception as e:
            raise DatabaseError(f"Failed to acquire connection: {e}")

    def release(self, conn: sqlite3.Connection) -> None:
        """Release a connection back to the pool."""
        try:
            with self._lock:
                if len(self._pool) < self.max_connections:
                    conn_id = id(conn)
                    self._pool[conn_id] = conn
                else:
                    conn.close()
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to release connection: {e}")

    def close_all(self) -> None:
        """Close all connections in the pool."""
        try:
            with self._lock:
                for cid, conn in list(self._pool.items()):
                    try:
                        conn.close()
                    except sqlite3.Error:
                        conn.close()
                    del self._pool[cid]
        except Exception as e:
            raise DatabaseError(f"Failed to close connections: {}")


class DbHandler:
    """Database handler with CRUD operations."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or os.environ.get("DB_PATH", "app.db")
        self.pool = ConnectionPool(self.db_path)
        try:
            self._init_schema()
        except DatabaseError:
            raise

    def _init_schema(self) -> None:
        """Create initial database schema."""
        conn = None
        try:
            conn = self.pool.acquire()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    email TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        except sqlite3.Error as e:
            raise DatabaseError(f"Schema init failed: {e}")
        finally:
            if conn:
                self.pool.release(conn)

    def create_user(self, username: str, password: str, email: str | None = None) -> dict[str, Any]:
        """Create a new user."""
        conn = None
        try:
            conn = self.pool.acquire()
            cursor = conn.execute(
                "INSERT INTO users (username, password, email) VALUES (?, ?, ?)",
                (username, password, email),
            )
            conn.commit()
            return {"id": cursor.lastrowid, "username": username, "email": email}
        except sqlite3.IntegrityError:
            raise DatabaseError(f"User '{username}' already exists")
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to create user: {e}")
        finally:
            if conn:
                self.pool.release(conn)

    def get_user(self, user_id: int) -> dict[str, Any] | None:
        """Retrieve a user by ID."""
        conn = None
        try:
            conn = self.pool.acquire()
            cursor = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to fetch user: {e}")
        finally:
            if conn:
                self.pool.release(conn)

    def close(self) -> None:
        """Close all database connections."""
        try:
            self.pool.close_all()
        except Exception as e:
            raise DatabaseError(f"Failed to close database: {e}")
"""

TEMPLATE_TEST = """import json
import os
import tempfile
import time

import pytest

from auth_handler import (
    AuthenticationError,
    login,
    logout,
    validate_token,
    _generate_token,
    _verify_password,
    _load_user_database,
    TOKEN_EXPIRY_SECONDS,
)


def test_login_successful():
    """Should return a token on successful login."""
    db_path = _create_test_user_db("testuser", "pass123")
    try:
        result = login("testuser", "pass123", db_path)
        assert "token" in result
        assert result["username"] == "testuser"
    finally:
        os.unlink(db_path)


def test_login_fails_wrong_password():
    """Should raise for wrong password."""
    db_path = _create_test_user_db("testuser", "correct")
    try:
        with pytest.raises(AuthenticationError):
            login("testuser", "wrong", db_path)
    finally:
        os.unlink(db_path)


def test_login_fails_nonexistent_user():
    """Should raise for unknown user."""
    db_path = _create_test_user_db("exists", "pass")
    try:
        with pytest.raises(AuthenticationError):
            login("nobody", "pass", db_path)
    finally:
        os.unlink(db_path)


def test_login_empty_credentials():
    """Should raise for empty username or password."""
    with pytest.raises(AuthenticationError):
        login("", "pass")
    with pytest.raises(AuthenticationError):
        login("user", "")


def test_logout_removes_token():
    """Should remove token from store."""
    token = _generate_token("testuser")
    store = {token: time.time() + 3600}
    logout(token, store)
    assert token not in store


def test_validate_token_active():
    """Should validate an active token."""
    token = _generate_token("testuser")
    store = {token: time.time() + 3600}
    result = validate_token(token, store)
    assert result["valid"] is True


def test_validate_token_expired():
    """Should reject an expired token."""
    token = _generate_token("testuser")
    store = {token: time.time() - 1}
    with pytest.raises(AuthenticationError, match="expired"):
        validate_token(token, store)


def test_validate_token_invalid():
    """Should reject unknown token."""
    with pytest.raises(AuthenticationError):
        validate_token("bogus", {})


def test_full_flow():
    """Full login → validate → logout → fail flow."""
    db_path = _create_test_user_db("flow_user", "flow_pass")
    try:
        result = login("flow_user", "flow_pass", db_path)
        token = result["token"]
        store = {token: time.time() + TOKEN_EXPIRY_SECONDS}
        assert validate_token(token, store)["valid"] is True
        logout(token, store)
        with pytest.raises(AuthenticationError):
            validate_token(token, store)
    finally:
        os.unlink(db_path)


def _create_test_user_db(username: str, password: str) -> str:
    """Helper to create a temp user database."""
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({username: {"password": password}}, f)
    return path
"""


def cmd_init(args):
    """Initialize a new Verdict project."""
    name = args.name
    path = Path.cwd() / name

    if path.exists():
        print(f"[ERROR] Directory '{name}' already exists")
        sys.exit(1)

    path.mkdir(parents=True)
    tests_dir = path / "tests"
    tests_dir.mkdir()

    files = {
        "plan.md": TEMPLATE_PLAN,
        "auth_handler.py": TEMPLATE_AUTH,
        "db_handler.py": TEMPLATE_DB,
        "tests/test_auth_handler.py": TEMPLATE_TEST,
    }

    for file_path, content in files.items():
        full = path / file_path
        full.write_text(content, encoding="utf-8")
        print(f"  [CREATED] {file_path}")

    print(f"\n✅ Verdict project '{name}' initialized!")
    print(f"\nNext steps:")
    print(f"  cd {name}")
    print(f"  pip install -r requirements.txt  # or: pip install verdict-mcp")
    print(f"  python -m verdict_mcp             # start MCP server")
    print(f"  python -m verdict_mcp.api_server   # start REST API")
    print(f"\nTasks: {len([f for f in files if f != 'plan.md'])} source files, {len([f for f in files if 'test' in f])} test file")


def cmd_verify(args):
    """Run Verdict checks on the current project."""
    plan = args.plan

    if not os.path.isfile(plan):
        print(f"[ERROR] Plan file not found: {plan}")
        sys.exit(1)

    sys.path.insert(0, str(Path.cwd()))

    try:
        from verdict_mcp.core.state_machine import project_state, TaskState
        from verdict_mcp.resources.master_plan import load_plan_into_state
        from verdict_mcp.tools import audit_task, enforce_ui
        from verdict_mcp.core.sandbox import run_pytest_with_coverage, run_mutation_testing
    except ImportError:
        print("[ERROR] Verdict not installed. Run: pip install verdict-mcp")
        sys.exit(1)

    result = load_plan_into_state(str(Path(plan).resolve()))
    print(f"📋 Plan: {result['task_count']} tasks loaded\n")

    all_passed = True

    for tid, tdata in result["tasks"].items():
        task = project_state.get_task(tid)
        for dep in task.dependencies:
            dep_task = project_state.get_task(dep)
            dep_task.state = TaskState.COMPLETED

        files = task.files
        audit_result = audit_task.execute(tid, files)
        status = "✅ PASSED" if audit_result["success"] else "❌ FAILED"
        print(f"  {status} {tid}: {task.title}")

        if not audit_result["success"]:
            all_passed = False
            for fr in audit_result.get("file_results", []):
                for e in fr.get("errors", []):
                    print(f"         {e}")

    ui_files = list(Path.cwd().glob("*_window.py")) + list(Path.cwd().glob("*ui*.py"))
    for uf in ui_files:
        ui_result = enforce_ui.execute(str(uf))
        status = "✅ UI OK" if ui_result["success"] else "❌ UI FAIL"
        print(f"  {status} {uf.name} (score: {ui_result['score']}%)")
        if not ui_result["success"]:
            all_passed = False
            for e in ui_result.get("errors", []):
                print(f"         {e}")

    test_files = list((Path.cwd() / "tests").glob("test_*.py"))
    for tf in test_files:
        target_name = tf.name.replace("test_", "")
        targets = list(Path.cwd().glob(target_name))
        if not targets:
            continue
        cov = run_pytest_with_coverage(str(tf), str(targets[0]), str(Path.cwd()))
        status = "✅ TESTS OK" if cov["success"] else "❌ TESTS FAIL"
        print(f"  {status} {tf.name} ({cov.get('coverage', 0)}% coverage)")
        if cov["success"]:
            mut = run_mutation_testing(str(tf), str(targets[0]), str(Path.cwd()))
            print(f"         Mutation score: {mut['mutation_score']}%")
            if not mut["success"]:
                all_passed = False

    print(f"\n{'✅ ALL CHECKS PASSED' if all_passed else '❌ SOME CHECKS FAILED'}")
    sys.exit(0 if all_passed else 1)


def cmd_list(args):
    """List available Verdict commands."""
    print("Verdict CLI — Code Quality Gatekeeper for AI Agents")
    print()
    print("Commands:")
    print("  verdict init <name>       Initialize a new Verdict project")
    print("  verdict verify [--plan]   Run Verdict checks on current project")
    print()
    print("Quick start:")
    print("  verdict init myproject")
    print("  cd myproject")
    print("  verdict verify")
    print()
    print("Run servers:")
    print("  python -m verdict_mcp               MCP server")
    print("  python -m verdict_mcp.api_server     REST API server")


def main():
    parser = argparse.ArgumentParser(description="Verdict — Code Quality Gatekeeper")
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init", help="Initialize a new project")
    init_parser.add_argument("name", help="Project name")

    verify_parser = subparsers.add_parser("verify", help="Run Verdict checks")
    verify_parser.add_argument("--plan", default="plan.md", help="Path to plan.md")

    subparsers.add_parser("help", help="Show help")

    args = parser.parse_args()

    if args.command == "init":
        cmd_init(args)
    elif args.command == "verify":
        cmd_verify(args)
    else:
        cmd_list(args)


if __name__ == "__main__":
    main()
