import time

import jwt

from app import config
from tests.conftest import register


def test_health_is_public(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_endpoints_need_login(client):
    for method, url in [("post", "/api/ask"), ("post", "/api/agent"), ("get", "/api/history"),
                        ("get", "/api/schema"), ("post", "/api/explain")]:
        r = client.request(method.upper(), url, json={"question": "x", "sql": "SELECT 1"})
        assert r.status_code == 401, url


def test_register_login_me(client):
    headers = register(client, "alice")
    assert client.get("/api/auth/me", headers=headers).json() == {"username": "alice"}
    r = client.post("/api/auth/login", json={"username": "ALICE", "password": "correct-horse"})
    assert r.status_code == 200  # usernames are case-insensitive


def test_duplicate_username_rejected(client):
    register(client, "alice")
    r = client.post("/api/auth/register", json={"username": "Alice", "password": "another-pass"})
    assert r.status_code == 409


def test_weak_input_rejected(client):
    assert client.post("/api/auth/register", json={"username": "bob", "password": "short"}).status_code == 400
    assert client.post("/api/auth/register", json={"username": "b!", "password": "long-enough-pw"}).status_code == 400


def test_wrong_password_and_unknown_user(client):
    register(client, "alice")
    assert client.post("/api/auth/login", json={"username": "alice", "password": "nope-nope-nope"}).status_code == 401
    assert client.post("/api/auth/login", json={"username": "ghost", "password": "whatever-pw"}).status_code == 401


def test_bad_and_expired_tokens(client):
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
    expired = jwt.encode({"sub": "1", "exp": int(time.time()) - 10}, config.SECRET_KEY, algorithm="HS256")
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401


def test_registration_can_be_disabled(client, monkeypatch):
    monkeypatch.setattr(config, "ALLOW_REGISTRATION", False)
    r = client.post("/api/auth/register", json={"username": "carol", "password": "correct-horse"})
    assert r.status_code == 403


def test_passwords_are_not_stored_in_plain_text(client):
    register(client, "alice", "correct-horse")
    from app import store
    assert "correct-horse" not in store.get_user_by_name("alice")["password_hash"]
