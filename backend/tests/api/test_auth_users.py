"""Auth, own profile and health endpoints (BE-TST-02, BE-AUTH-01..04)."""
from tests.api.conftest import TEST_PASSWORD, error_code


def test_health_is_public(anonymous_client):
    response = anonymous_client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_register_returns_user_without_password(anonymous_client):
    response = anonymous_client.post(
        "/api/auth/register",
        json={"name": " Ana ", "email": "Ana@Example.com", "password": "longenough1"},
    )
    assert response.status_code == 201
    body = response.get_json()
    assert body["name"] == "Ana"
    assert body["email"] == "ana@example.com"
    assert "password" not in body and "password_hash" not in body


def test_register_rejects_unknown_role_field(anonymous_client):
    response = anonymous_client.post(
        "/api/auth/register",
        json={"name": "X", "email": "x@example.com", "password": "longenough1", "role": "admin"},
    )
    assert response.status_code == 422
    assert error_code(response) == "VALIDATION_ERROR"


def test_register_duplicate_email_is_409(anonymous_client, people):
    response = anonymous_client.post(
        "/api/auth/register",
        json={"name": "Dup", "email": people["admin"].email.upper(), "password": "longenough1"},
    )
    assert response.status_code == 409
    assert error_code(response) == "EMAIL_TAKEN"


def test_login_returns_bearer_token_and_lifetime(anonymous_client, people):
    response = anonymous_client.post(
        "/api/auth/login", json={"email": "ADMIN@example.com", "password": TEST_PASSWORD}
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["token_type"] == "Bearer"
    assert body["expires_in"] == 3600
    assert body["access_token"]


def test_login_wrong_password_and_unknown_email_share_one_error(anonymous_client, people):
    wrong = anonymous_client.post(
        "/api/auth/login", json={"email": "admin@example.com", "password": "nope-nope"}
    )
    unknown = anonymous_client.post(
        "/api/auth/login", json={"email": "nobody@example.com", "password": TEST_PASSWORD}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert error_code(wrong) == error_code(unknown) == "UNAUTHENTICATED"
    assert wrong.get_json() == unknown.get_json()


def test_login_missing_field_is_422(anonymous_client):
    response = anonymous_client.post("/api/auth/login", json={"email": "a@example.com"})
    assert response.status_code == 422


def test_me_requires_token(anonymous_client):
    response = anonymous_client.get("/api/users/me")
    assert response.status_code == 401
    assert error_code(response) == "UNAUTHENTICATED"


def test_me_with_invalid_token_is_401(anonymous_client):
    response = anonymous_client.get(
        "/api/users/me", headers={"Authorization": "Bearer not-a-token"}
    )
    assert response.status_code == 401
    assert error_code(response) == "UNAUTHENTICATED"


def test_me_returns_own_profile(member_client, people):
    response = member_client.get("/api/users/me")
    assert response.status_code == 200
    body = response.get_json()
    assert body["id"] == str(people["member"].id)
    assert body["email"] == "member@example.com"
    assert body["created_at"].endswith("Z")


def test_patch_me_updates_name(member_client):
    response = member_client.patch("/api/users/me", json={"name": "Renamed"})
    assert response.status_code == 200
    assert response.get_json()["name"] == "Renamed"


def test_patch_me_empty_body_is_422(member_client):
    response = member_client.patch("/api/users/me", json={})
    assert response.status_code == 422


def test_patch_me_rejects_password_field(member_client):
    response = member_client.patch("/api/users/me", json={"password": "x" * 10})
    assert response.status_code == 422


def test_patch_me_email_taken_is_409(member_client, people):
    response = member_client.patch("/api/users/me", json={"email": "admin@example.com"})
    assert response.status_code == 409
    assert error_code(response) == "EMAIL_TAKEN"


def test_patch_me_requires_token(anonymous_client):
    response = anonymous_client.patch("/api/users/me", json={"name": "x"})
    assert response.status_code == 401
