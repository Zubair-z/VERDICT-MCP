"""Tests for the authentication handler module."""
import json
import os
import tempfile
import time
from unittest.mock import patch, MagicMock

import pytest

from auth_handler import (
    AuthenticationError,
    login,
    logout,
    validate_token,
    _generate_token,
    _verify_password,
    _load_user_database,
    _active_tokens,
    TOKEN_EXPIRY_SECONDS,
)


def test_load_user_database_returns_empty_dict_when_file_missing():
    """Should return empty dict when file does not exist."""
    result = _load_user_database("nonexistent_users.json")
    assert result == {}


def test_load_user_database_parses_valid_json():
    """Should parse and return valid JSON content."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump({"alice": {"password": "secret"}}, f)
        f.flush()
        path = f.name
    try:
        result = _load_user_database(path)
        assert result == {"alice": {"password": "secret"}}
    finally:
        os.unlink(path)


def test_load_user_database_raises_on_invalid_json():
    """Should raise AuthenticationError on malformed JSON."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        f.write("not json")
        f.flush()
        path = f.name
    try:
        with pytest.raises(AuthenticationError, match="Invalid user database"):
            _load_user_database(path)
    finally:
        os.unlink(path)


def test_verify_password_returns_true_for_correct_password():
    """Should return True when password matches stored value."""
    stored = {"password": "my_pass"}
    assert _verify_password(stored, "my_pass") is True


def test_verify_password_returns_false_for_wrong_password():
    """Should return False when password does not match."""
    stored = {"password": "my_pass"}
    assert _verify_password(stored, "wrong_pass") is False


def test_verify_password_returns_false_when_key_missing():
    """Should return False when no password key in stored data."""
    stored = {}
    assert _verify_password(stored, "anything") is False


def test_generate_token_returns_string():
    """Should return a non-empty string token."""
    token = _generate_token("testuser")
    assert isinstance(token, str)
    assert len(token) > 0


def test_generate_token_different_for_different_users():
    """Should generate different tokens for different usernames."""
    t1 = _generate_token("user1")
    t2 = _generate_token("user2")
    assert t1 != t2


def test_login_successful_returns_token():
    """Should return a token dict on successful login."""
    db_path = _create_test_user_db("test_login_user", "pass123")
    try:
        result = login("test_login_user", "pass123", db_path)
        assert "token" in result
        assert result["username"] == "test_login_user"
        assert result["expires_in"] == TOKEN_EXPIRY_SECONDS
    finally:
        os.unlink(db_path)


def test_login_fails_with_wrong_password():
    """Should raise AuthenticationError for wrong password."""
    db_path = _create_test_user_db("testuser", "correct_pass")
    try:
        with pytest.raises(AuthenticationError, match="Invalid username or password"):
            login("testuser", "wrong_pass", db_path)
    finally:
        os.unlink(db_path)


def test_login_fails_with_nonexistent_user():
    """Should raise AuthenticationError for unknown username."""
    db_path = _create_test_user_db("existing_user", "pass")
    try:
        with pytest.raises(AuthenticationError, match="Invalid username or password"):
            login("nonexistent", "pass", db_path)
    finally:
        os.unlink(db_path)


def test_login_fails_with_empty_username():
    """Should raise AuthenticationError when username is empty."""
    with pytest.raises(AuthenticationError, match="Username and password are required"):
        login("", "password")


def test_login_fails_with_empty_password():
    """Should raise AuthenticationError when password is empty."""
    with pytest.raises(AuthenticationError, match="Username and password are required"):
        login("user", "")


def test_logout_returns_true():
    """Should return True on successful logout."""
    token = _generate_token("testuser")
    store = {token: time.time() + 3600}
    result = logout(token, store)
    assert result is True
    assert token not in store


def test_logout_removes_token_from_store():
    """Should remove the token from the store."""
    token = _generate_token("testuser")
    store = {token: time.time() + 3600}
    logout(token, store)
    assert token not in store


def test_logout_handles_nonexistent_token():
    """Should not raise when token does not exist in store."""
    store = {}
    result = logout("nonexistent_token", store)
    assert result is True


def test_logout_raises_on_empty_token():
    """Should raise AuthenticationError for empty token."""
    with pytest.raises(AuthenticationError, match="Token is required"):
        logout("")


def test_validate_token_returns_valid_for_active_token():
    """Should return valid=True for an active token."""
    token = _generate_token("testuser")
    store = {token: time.time() + 3600}
    result = validate_token(token, store)
    assert result["valid"] is True
    assert "username" in result


def test_validate_token_raises_for_expired_token():
    """Should raise AuthenticationError when token is expired."""
    token = _generate_token("testuser")
    store = {token: time.time() - 1}
    with pytest.raises(AuthenticationError, match="Token has expired"):
        validate_token(token, store)


def test_validate_token_removes_expired_token_from_store():
    """Should remove expired token from the store on validation."""
    token = _generate_token("testuser")
    store = {token: time.time() - 1}
    with pytest.raises(AuthenticationError):
        validate_token(token, store)
    assert token not in store


def test_validate_token_raises_for_invalid_token():
    """Should raise AuthenticationError for unknown token."""
    store = {}
    with pytest.raises(AuthenticationError, match="Invalid or expired token"):
        validate_token("bogus_token", store)


def test_validate_token_raises_for_empty_token():
    """Should raise AuthenticationError when token is empty."""
    with pytest.raises(AuthenticationError, match="Token is required"):
        validate_token("")


def test_validate_token_raises_for_none_token():
    """Should raise AuthenticationError when token is None."""
    with pytest.raises(AuthenticationError, match="Token is required"):
        validate_token(None)  # type: ignore[arg-type]


def test_login_and_validate_end_to_end():
    """Should successfully login and validate the returned token."""
    db_path = _create_test_user_db("e2e_user", "e2e_pass")
    try:
        result = login("e2e_user", "e2e_pass", db_path)
        token = result["token"]
        store = {token: time.time() + TOKEN_EXPIRY_SECONDS}
        validation = validate_token(token, store)
        assert validation["valid"] is True
    finally:
        os.unlink(db_path)


def test_login_logout_validate_flow():
    """Should fail to validate a token after logout."""
    db_path = _create_test_user_db("flow_user", "flow_pass")
    try:
        result = login("flow_user", "flow_pass", db_path)
        token = result["token"]
        store = {token: time.time() + TOKEN_EXPIRY_SECONDS}
        logout(token, store)
        with pytest.raises(AuthenticationError, match="Invalid or expired token"):
            validate_token(token, store)
    finally:
        os.unlink(db_path)


def test_login_with_env_db_path():
    """Should use AUTH_DB_PATH env var when no db_path provided."""
    db_path = _create_test_user_db("env_user", "env_pass")
    try:
        with patch.dict(os.environ, {"AUTH_DB_PATH": db_path}):
            result = login("env_user", "env_pass")
            assert result["username"] == "env_user"
    finally:
        os.unlink(db_path)


def test_login_uses_default_db_path_fallback():
    """Should use default users.json when no db_path or env var set."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(AuthenticationError, match="Invalid username or password"):
            login("any_user", "any_pass")


def test_validate_token_respects_expiry():
    """Should return correct expiry time in validation result."""
    token = _generate_token("testuser")
    future = time.time() + 100
    store = {token: future}
    result = validate_token(token, store)
    assert result["expires_at"] == future


def test_logout_with_default_store():
    """Should work with the module-level active tokens store."""
    initial_len = len(_active_tokens)
    result = logout("nonexistent_default", _active_tokens)
    assert result is True
    assert len(_active_tokens) == initial_len


def test_verify_password_raises_on_invalid_stored_type():
    """Should raise AuthenticationError for non-dict stored data."""
    with pytest.raises(AuthenticationError, match="Invalid credential format"):
        _verify_password(None, "pass")  # type: ignore[arg-type]


def test_login_raises_on_corrupt_db():
    """Should re-raise AuthenticationError when db file has invalid JSON."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        f.write("{{{corrupt")
        f.flush()
        path = f.name
    try:
        with pytest.raises(AuthenticationError, match="Invalid user database"):
            login("user", "pass", path)
    finally:
        os.unlink(path)


def test_logout_raises_on_store_error():
    """Should wrap unexpected store errors."""
    class BrokenStore(dict):
        def pop(self, *args, **kwargs):
            raise RuntimeError("store failure")
    store = BrokenStore()
    with pytest.raises(AuthenticationError, match="Logout failed"):
        logout("sometoken", store)


def test_validate_token_wraps_unexpected_error():
    """Should wrap unexpected validation errors."""
    class BrokenStore(dict):
        def get(self, *args, **kwargs):
            raise RuntimeError("unexpected error")
    store = BrokenStore()
    with pytest.raises(AuthenticationError, match="Token validation error"):
        validate_token("sometoken", store)


def _create_test_user_db(username: str, password: str) -> str:
    """Create a temporary user database file."""
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({username: {"password": password}}, f)
    return path
