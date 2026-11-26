"""Flows that cross endpoints (BE-TST-04)."""
from app.extensions import db
from app.models import BoardMember, Card, Notification
from tests.api.conftest import error_code


def test_creator_of_board_is_admin_on_detail(anonymous_client, member_client, make_user):
    created = member_client.post("/api/boards", json={"name": "Mine"}).get_json()
    detail = member_client.get(f"/api/boards/{created['id']}").get_json()
    assert detail["my_role"] == "admin"


def test_admin_adds_guest_as_member_who_can_then_create_card(
    admin_client, api_client, board, make_column, make_user
):
    newcomer = make_user("Newcomer", "newcomer@example.com")
    client = api_client(newcomer)
    column = make_column(board, name="Ops")
    assert client.post(f"/api/columns/{column.id}/cards", json={"title": "x"}).status_code == 403

    admin_client.post(
        f"/api/boards/{board.id}/members", json={"email": newcomer.email, "role": "member"}
    )
    response = client.post(f"/api/columns/{column.id}/cards", json={"title": "Now I can"})
    assert response.status_code == 201


def test_last_admin_cannot_be_demoted_or_removed(admin_client, board, people):
    assert admin_client.patch(
        f"/api/boards/{board.id}/members/{people['admin'].id}", json={"role": "member"}
    ).status_code == 409
    response = admin_client.delete(f"/api/boards/{board.id}/members/{people['admin'].id}")
    assert response.status_code == 409
    assert error_code(response) == "LAST_ADMIN"


def test_admin_deleting_member_card_notifies_creator_not_actor(
    admin_client, column, make_card, people
):
    card = make_card(column, people["member"])
    admin_client.delete(f"/api/cards/{card.id}")
    rows = db.session.query(Notification).all()
    assert any(n.user_id == people["member"].id and n.type == "card_deleted" for n in rows)
    assert all(n.user_id != people["admin"].id for n in rows)
    assert db.session.get(Card, card.id).deleted_at is not None


def test_rebalance_flag_false_on_plain_move(member_client, column, make_card, people):
    card = make_card(column, people["member"], order=1024.0)
    body = member_client.patch(
        f"/api/cards/{card.id}/position", json={"column_id": str(column.id), "order": 1536.0}
    ).get_json()
    assert body["rebalanced"] is False


def test_soft_deleted_card_disappears_from_board_and_analytics(
    member_client, admin_client, board, column, make_card, people
):
    card = make_card(column, people["member"], assignee=people["member"])
    member_client.delete(f"/api/cards/{card.id}")
    detail = member_client.get(f"/api/boards/{board.id}").get_json()
    assert detail["columns"]["items"][0]["cards"]["items"] == []
    analytics = admin_client.get(f"/api/boards/{board.id}/analytics").get_json()
    assert analytics["cards_per_column"][0]["total_cards"] == 0
    assert member_client.get("/api/cards?assignee=me").get_json()["items"] == []


def test_member_rejoin_membership_row_unchanged_by_failed_demotion(admin_client, board, people):
    admin_client.patch(f"/api/boards/{board.id}/members/{people['admin'].id}", json={"role": "member"})
    assert db.session.get(BoardMember, (board.id, people["admin"].id)).role == "admin"
