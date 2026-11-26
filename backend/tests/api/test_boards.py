"""Board endpoints and the role matrix for board actions (BE-TST-02, BE-TST-03)."""
from app.extensions import db
from app.models import Board, BoardMember
from tests.api.conftest import error_code


def test_create_board_makes_creator_admin(member_client, people):
    response = member_client.post("/api/boards", json={"name": "New"})
    assert response.status_code == 201
    body = response.get_json()
    assert body["my_role"] == "admin"
    assert body["is_public"] is True
    row = db.session.get(BoardMember, (body["id"], people["member"].id))
    assert row is not None and row.role == "admin"


def test_create_board_requires_token(anonymous_client):
    response = anonymous_client.post("/api/boards", json={"name": "New"})
    assert response.status_code == 401


def test_create_board_empty_name_is_422(member_client):
    response = member_client.post("/api/boards", json={"name": "   "})
    assert response.status_code == 422
    assert error_code(response) == "VALIDATION_ERROR"


def test_list_public_boards_for_anonymous(anonymous_client, board, private_board):
    response = anonymous_client.get("/api/boards")
    assert response.status_code == 200
    body = response.get_json()
    ids = [item["id"] for item in body["items"]]
    assert str(board.id) in ids and str(private_board.id) not in ids
    assert body["page"] == 1 and body["per_page"] == 20 and body["total"] == 1
    assert all(item["my_role"] == "anonymous" for item in body["items"])


def test_list_scope_mine_requires_token(anonymous_client):
    response = anonymous_client.get("/api/boards?scope=mine")
    assert response.status_code == 401


def test_list_scope_mine_shows_membership_including_private(member_client, board, private_board):
    response = member_client.get("/api/boards?scope=mine")
    assert response.status_code == 200
    roles = {item["id"]: item["my_role"] for item in response.get_json()["items"]}
    assert roles == {str(board.id): "member", str(private_board.id): "member"}


def test_list_scope_mine_excludes_non_members(outside_admin_client, board):
    response = outside_admin_client.get("/api/boards?scope=mine")
    assert response.status_code == 200
    assert str(board.id) not in [i["id"] for i in response.get_json()["items"]]


def test_list_invalid_scope_is_422(member_client):
    response = member_client.get("/api/boards?scope=all")
    assert response.status_code == 422


def test_list_per_page_over_max_is_422_not_clamped(anonymous_client):
    response = anonymous_client.get("/api/boards?per_page=101")
    assert response.status_code == 422


def test_get_public_board_anonymous_sees_columns_and_cards(
    anonymous_client, board, column, make_card, people
):
    card = make_card(column, people["member"], title="Visible", assignee=people["member"])
    response = anonymous_client.get(f"/api/boards/{board.id}")
    assert response.status_code == 200
    body = response.get_json()
    assert body["my_role"] == "anonymous"
    (col,) = body["columns"]["items"]
    (item,) = col["cards"]["items"]
    assert item["id"] == str(card.id)
    assert item["created_by"] == str(people["member"].id)
    assert item["assignee"] == {"id": str(people["member"].id), "name": people["member"].name}
    assert "email" not in item["assignee"]


def test_get_private_board_anonymous_is_404(anonymous_client, private_board):
    response = anonymous_client.get(f"/api/boards/{private_board.id}")
    assert response.status_code == 404
    assert error_code(response) == "NOT_FOUND"


def test_get_private_board_guest_is_404(guest_client, private_board):
    response = guest_client.get(f"/api/boards/{private_board.id}")
    assert response.status_code == 404


def test_get_public_board_guest_is_read_only_guest(guest_client, board):
    response = guest_client.get(f"/api/boards/{board.id}")
    assert response.status_code == 200
    assert response.get_json()["my_role"] == "guest"


def test_get_board_malformed_uuid_is_404(anonymous_client):
    response = anonymous_client.get("/api/boards/not-a-uuid")
    assert response.status_code == 404
    assert error_code(response) == "NOT_FOUND"


def test_get_board_hides_soft_deleted_cards(anonymous_client, board, column, make_card, people):
    from app.models import Card

    card = make_card(column, people["member"])
    card.soft_delete()
    db.session.commit()
    response = anonymous_client.get(f"/api/boards/{board.id}")
    assert response.get_json()["columns"]["items"][0]["cards"]["items"] == []


def test_patch_board_admin_ok(admin_client, board):
    response = admin_client.patch(f"/api/boards/{board.id}", json={"name": "Renamed", "is_public": False})
    assert response.status_code == 200
    body = response.get_json()
    assert body["name"] == "Renamed" and body["is_public"] is False and body["my_role"] == "admin"


def test_patch_board_member_is_403(member_client, board):
    response = member_client.patch(f"/api/boards/{board.id}", json={"name": "No"})
    assert response.status_code == 403
    assert error_code(response) == "FORBIDDEN"


def test_patch_board_guest_on_public_is_403(guest_client, board):
    response = guest_client.patch(f"/api/boards/{board.id}", json={"name": "No"})
    assert response.status_code == 403


def test_patch_board_outside_admin_on_public_is_403(outside_admin_client, board):
    response = outside_admin_client.patch(f"/api/boards/{board.id}", json={"name": "No"})
    assert response.status_code == 403


def test_patch_board_guest_on_private_is_404(guest_client, private_board):
    response = guest_client.patch(f"/api/boards/{private_board.id}", json={"name": "No"})
    assert response.status_code == 404


def test_patch_board_anonymous_is_401(anonymous_client, board):
    response = anonymous_client.patch(f"/api/boards/{board.id}", json={"name": "No"})
    assert response.status_code == 401


def test_patch_board_empty_body_is_422(admin_client, board):
    response = admin_client.patch(f"/api/boards/{board.id}", json={})
    assert response.status_code == 422


def test_delete_board_member_is_403(member_client, board):
    response = member_client.delete(f"/api/boards/{board.id}")
    assert response.status_code == 403


def test_delete_board_admin_cascades(admin_client, board, column, make_card, people):
    make_card(column, people["member"])
    response = admin_client.delete(f"/api/boards/{board.id}")
    assert response.status_code == 204
    assert response.data == b""
    assert db.session.get(Board, board.id) is None


def test_delete_board_anonymous_is_401(anonymous_client, board):
    assert anonymous_client.delete(f"/api/boards/{board.id}").status_code == 401
