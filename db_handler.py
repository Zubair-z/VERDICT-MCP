import json
import os
import sqlite3
import threading
from collections import OrderedDict
from typing import Any


class DatabaseError(Exception):
    """Raised when a database operation fails."""


class ConnectionPool:
    """A thread-safe SQLite connection pool."""

    def __init__(self, db_path: str, max_connections: int = 5):
        """Initialize the connection pool with a database path."""
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
            raise DatabaseError(f"Failed to close connections: {e}")


class DbHandler:
    """Database handler with CRUD operations for user data."""

    def __init__(self, db_path: str | None = None):
        """Initialize the database handler with an optional path."""
        self.db_path = db_path or os.environ.get("DB_PATH", "app.db")
        self.pool = ConnectionPool(self.db_path)
        try:
            self._init_schema()
        except DatabaseError:
            raise

    def _init_schema(self) -> None:
        """Create the initial database schema if it doesn't exist."""
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
            raise DatabaseError(f"Schema initialization failed: {e}")
        finally:
            if conn:
                self.pool.release(conn)

    def create_user(self, username: str, password: str, email: str | None = None) -> dict[str, Any]:
        """Create a new user in the database."""
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
        """Retrieve a user by their ID."""
        conn = None
        try:
            conn = self.pool.acquire()
            cursor = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            if row is None:
                return None
            return dict(row)
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to fetch user: {e}")
        finally:
            if conn:
                self.pool.release(conn)

    def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        """Retrieve a user by their username."""
        conn = None
        try:
            conn = self.pool.acquire()
            cursor = conn.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            if row is None:
                return None
            return dict(row)
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to fetch user by username: {e}")
        finally:
            if conn:
                self.pool.release(conn)

    def update_user(self, user_id: int, **fields: Any) -> dict[str, Any]:
        """Update user fields by user ID."""
        conn = None
        try:
            allowed = {"password", "email"}
            updates = {k: v for k, v in fields.items() if k in allowed}
            if not updates:
                raise DatabaseError("No valid fields to update")

            set_clause = ", ".join(f"{k} = ?" for k in updates)
            values = list(updates.values()) + [user_id]

            conn = self.pool.acquire()
            conn.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
            conn.commit()

            return self.get_user(user_id) or {"error": "User not found"}
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to update user: {e}")
        finally:
            if conn:
                self.pool.release(conn)

    def delete_user(self, user_id: int) -> bool:
        """Delete a user by their ID."""
        conn = None
        try:
            conn = self.pool.acquire()
            cursor = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to delete user: {e}")
        finally:
            if conn:
                self.pool.release(conn)

    def list_users(self) -> list[dict[str, Any]]:
        """List all users in the database."""
        conn = None
        try:
            conn = self.pool.acquire()
            cursor = conn.execute("SELECT id, username, email, created_at FROM users ORDER BY id")
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to list users: {e}")
        finally:
            if conn:
                self.pool.release(conn)

    def close(self) -> None:
        """Close all database connections."""
        try:
            self.pool.close_all()
        except Exception as e:
            raise DatabaseError(f"Failed to close database: {e}")
