"""Board member management (BE-AZ-07, BE-AZ-06, DB-MEM-02)."""
from app.extensions import db
from app.models import BoardMember
from tests.api.conftest import error_code


def test_list_members_admin_sees_emails(admin_client, board, people):
    response = admin_client.get(f"/api/boards/{board.id}/members")
    assert response.status_code == 200
    items = response.get_json()["items"]
    assert len(items) == 3
    assert all(item["email"] for item in items)


def test_list_members_member_sees_no_emails(member_client, board):
    response = member_client.get(f"/api/boards/{board.id}/members")
    assert response.status_code == 200
    assert all(item["email"] is None for item in response.get_json()["items"])


def test_list_members_guest_on_public_board_is_403(guest_client, board):
    response = guest_client.get(f"/api/boards/{board.id}/members")
    assert response.status_code == 403


def test_list_members_requires_token(anonymous_client, board):
    assert anonymous_client.get(f"/api/boards/{board.id}/members").status_code == 401


def test_add_member_by_email_creates_row_and_notifies(admin_client, board, make_user):
    newcomer = make_user("New Comer", "new@example.com")
    response = admin_client.post(
        f"/api/boards/{board.id}/members", json={"email": "NEW@example.com", "role": "member"}
    )
    assert response.status_code == 201
    assert response.get_json()["user_id"] == str(newcomer.id)
    assert db.session.get(BoardMember, (board.id, newcomer.id)).role == "member"


def test_add_member_unknown_email_is_422(admin_client, board):
    response = admin_client.post(
        f"/api/boards/{board.id}/members", json={"email": "ghost@example.com", "role": "member"}
    )
    assert response.status_code == 422
    assert error_code(response) == "VALIDATION_ERROR"


def test_add_existing_member_is_409(admin_client, board, people):
    response = admin_client.post(
        f"/api/boards/{board.id}/members", json={"email": "member@example.com", "role": "member"}
    )
    assert response.status_code == 409
    assert error_code(response) == "ALREADY_MEMBER"


def test_add_member_invalid_role_is_422(admin_client, board, make_user):
    make_user("Role Test", "role@example.com")
    response = admin_client.post(
        f"/api/boards/{board.id}/members", json={"email": "role@example.com", "role": "guest"}
    )
    assert response.status_code == 422


def test_add_member_by_member_is_403(member_client, board, make_user):
    make_user("Blocked", "blocked@example.com")
    response = member_client.post(
        f"/api/boards/{board.id}/members", json={"email": "blocked@example.com", "role": "member"}
    )
    assert response.status_code == 403


def test_add_member_anonymous_is_401(anonymous_client, board):
    response = anonymous_client.post(
        f"/api/boards/{board.id}/members", json={"email": "x@example.com", "role": "member"}
    )
    assert response.status_code == 401


def test_promote_member_to_admin(admin_client, board, people):
    response = admin_client.patch(
        f"/api/boards/{board.id}/members/{people['member'].id}", json={"role": "admin"}
    )
    assert response.status_code == 200
    assert response.get_json()["role"] == "admin"


def test_demote_last_admin_is_409(admin_client, board, people):
    response = admin_client.patch(
        f"/api/boards/{board.id}/members/{people['admin'].id}", json={"role": "member"}
    )
    assert response.status_code == 409
    assert error_code(response) == "LAST_ADMIN"


def test_demote_one_of_two_admins_succeeds(admin_client, board, people):
    db.session.get(BoardMember, (board.id, people["member"].id)).role = "admin"
    db.session.commit()
    response = admin_client.patch(
        f"/api/boards/{board.id}/members/{people['admin'].id}", json={"role": "member"}
    )
    assert response.status_code == 200


def test_update_member_unknown_user_is_404(admin_client, board, people):
    response = admin_client.patch(
        f"/api/boards/{board.id}/members/{people['guest'].id}", json={"role": "member"}
    )
    assert response.status_code == 404


def test_update_member_empty_body_is_422(admin_client, board, people):
    response = admin_client.patch(
        f"/api/boards/{board.id}/members/{people['member'].id}", json={}
    )
    assert response.status_code == 422


def test_remove_member_clears_their_assignments(admin_client, board, people, make_column, make_card):
    column = make_column(board)
    card = make_card(column, people["admin"], assignee=people["member"])
    response = admin_client.delete(f"/api/boards/{board.id}/members/{people['member'].id}")
    assert response.status_code == 204
    db.session.refresh(card)
    assert card.assignee_id is None
    assert db.session.get(BoardMember, (board.id, people["member"].id)) is None


def test_remove_last_admin_is_409(admin_client, board, people):
    response = admin_client.delete(f"/api/boards/{board.id}/members/{people['admin'].id}")
    assert response.status_code == 409
    assert error_code(response) == "LAST_ADMIN"


def test_remove_non_member_is_404(admin_client, board, people):
    response = admin_client.delete(f"/api/boards/{board.id}/members/{people['guest'].id}")
    assert response.status_code == 404


def test_removed_member_loses_write_access(member_client, admin_client, board, people, make_column):
    make_column(board)
    admin_client.delete(f"/api/boards/{board.id}/members/{people['member'].id}")
    response = member_client.post(f"/api/boards/{board.id}/columns", json={"name": "Nope"})
    assert response.status_code == 403
