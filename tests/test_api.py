import asyncio
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import get_settings
from app.models import User
from app.security import ALGORITHM, get_secret_key
from main import create_app


def register(client, username="alice", email="alice@example.com", password="Password1!"):
    return client.post(
        "/users",
        json={"username": username, "email": email, "password": password},
    )


def login(client, username="alice", password="Password1!"):
    return client.post("/login", json={"username": username, "password": password})


def auth_headers(client, username="alice", email="alice@example.com"):
    register(client, username=username, email=email)
    response = login(client, username=username)
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_register_user_success(client):
    response = register(client)

    assert response.status_code == 201
    assert response.json()["username"] == "alice"
    assert response.json()["email"] == "alice@example.com"
    assert "password" not in response.json()


def test_register_accepts_any_string_punctuation_as_special_character(client):
    response = register(client, password="Password1+")

    assert response.status_code == 201


@pytest.mark.parametrize("password", ["short", "password1", "PASSWORD1", "Password", "Password1"])
def test_register_rejects_weak_passwords(client, password):
    response = register(client, password=password)

    assert response.status_code == 422


def test_register_stores_password_hash_not_plaintext(client, db_session):
    register(client)

    async def get_user():
        async with db_session() as session:
            return await session.scalar(select(User).where(User.username == "alice"))

    user = asyncio.run(get_user())

    assert user is not None
    assert user.password_hash != "Password1!"
    assert "**********" not in user.password_hash
    assert user.password_hash.startswith("pbkdf2_sha256$")


def test_register_rejects_duplicate_username_and_email(client):
    register(client)

    username_response = register(
        client,
        username="alice",
        email="alice2@example.com",
    )
    email_response = register(
        client,
        username="alice2",
        email="alice@example.com",
    )

    assert username_response.status_code == 409
    assert email_response.status_code == 409


def test_login_success_and_failure(client):
    register(client)

    success = login(client)
    failure = login(client, password="wrong-password")

    assert success.status_code == 200
    assert success.json()["token_type"] == "bearer"
    assert success.json()["access_token"]
    assert failure.status_code == 401


@pytest.mark.parametrize(
    ("method", "path", "json"),
    [
        ("post", "/posts", {"content": "hello"}),
        ("get", "/posts", None),
        ("post", "/users/follow/bob", None),
        ("delete", "/users/follow/bob", None),
    ],
)
def test_protected_endpoints_require_token(client, method, path, json):
    request = getattr(client, method)
    response = request(path, json=json) if json is not None else request(path)

    assert response.status_code == 401


@pytest.mark.parametrize(
    "headers",
    [
        {"Authorization": "Bearer not-a-jwt"},
        {
            "Authorization": "Bearer "
            + jwt.encode(
                {
                    "sub": "1",
                    "exp": datetime.now(UTC) - timedelta(minutes=1),
                },
                get_secret_key(),
                algorithm=ALGORITHM,
            )
        },
    ],
)
def test_protected_endpoint_rejects_invalid_or_expired_token(client, headers):
    response = client.get("/posts", headers=headers)

    assert response.status_code == 401


def test_create_post(client):
    headers = auth_headers(client)

    response = client.post("/posts", json={"content": "hello world"}, headers=headers)

    assert response.status_code == 201
    assert response.json()["content"] == "hello world"
    assert response.json()["author"]["username"] == "alice"


def test_feed_includes_followed_users_posts(client):
    alice_headers = auth_headers(client, username="alice", email="alice@example.com")
    bob_headers = auth_headers(client, username="bob", email="bob@example.com")
    charlie_headers = auth_headers(client, username="charlie", email="charlie@example.com")

    client.post("/posts", json={"content": "from alice"}, headers=alice_headers)
    client.post("/posts", json={"content": "from bob"}, headers=bob_headers)
    client.post("/posts", json={"content": "from charlie"}, headers=charlie_headers)
    client.post("/users/follow/bob", headers=alice_headers)

    response = client.get("/posts", headers=alice_headers)

    assert response.status_code == 200
    contents = [post["content"] for post in response.json()]
    assert "from alice" in contents
    assert "from bob" in contents
    assert "from charlie" not in contents


def test_follow_rejects_self_and_duplicate_follow(client):
    alice_headers = auth_headers(client, username="alice", email="alice@example.com")
    register(client, username="bob", email="bob@example.com")

    self_follow = client.post("/users/follow/alice", headers=alice_headers)
    first_follow = client.post("/users/follow/bob", headers=alice_headers)
    duplicate_follow = client.post("/users/follow/bob", headers=alice_headers)

    assert self_follow.status_code == 400
    assert first_follow.status_code == 200
    assert duplicate_follow.status_code == 409


def test_unfollow_removes_user_from_feed(client):
    alice_headers = auth_headers(client, username="alice", email="alice@example.com")
    bob_headers = auth_headers(client, username="bob", email="bob@example.com")

    client.post("/posts", json={"content": "from bob"}, headers=bob_headers)
    client.post("/users/follow/bob", headers=alice_headers)
    before_unfollow = client.get("/posts", headers=alice_headers)
    unfollow = client.delete("/users/follow/bob", headers=alice_headers)
    after_unfollow = client.get("/posts", headers=alice_headers)

    assert "from bob" in [post["content"] for post in before_unfollow.json()]
    assert unfollow.status_code == 204
    assert "from bob" not in [post["content"] for post in after_unfollow.json()]


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1"])
def test_feed_rejects_invalid_pagination_bounds(client, query):
    headers = auth_headers(client)

    response = client.get(f"/posts?{query}", headers=headers)

    assert response.status_code == 422


def test_app_startup_fails_without_secret_key(tmp_path, monkeypatch):
    get_settings.cache_clear()
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        with TestClient(create_app()):
            pass
    get_settings.cache_clear()
