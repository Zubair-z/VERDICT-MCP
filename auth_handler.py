import json
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


def _verify_password(stored: dict[str, Any], password: str) -> bool:
    """Verify a password against stored credentials."""
    try:
        return stored.get("password") == password
    except AttributeError as e:
        raise AuthenticationError(f"Invalid credential format: {e}")


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

    if not _verify_password(user, password):
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
