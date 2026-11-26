"""Column endpoints, Member and Admin deletion rules, reorder (BE-TST-02, BE-TST-03, BE-AZ-04)."""
from app.extensions import db
from app.models import BoardColumn, Card
from tests.api.conftest import error_code


def test_create_column_appends_to_end(member_client, board, column):
    response = member_client.post(f"/api/boards/{board.id}/columns", json={"name": "Done soon"})
    assert response.status_code == 201
    body = response.get_json()
    assert body["order"] == 2048.0
    assert body["is_done"] is False
    assert body["created_by"] is not None


def test_create_column_guest_is_403(guest_client, board):
    response = guest_client.post(f"/api/boards/{board.id}/columns", json={"name": "X"})
    assert response.status_code == 403


def test_create_column_anonymous_is_401(anonymous_client, board):
    response = anonymous_client.post(f"/api/boards/{board.id}/columns", json={"name": "X"})
    assert response.status_code == 401


def test_create_column_missing_name_is_422(member_client, board):
    response = member_client.post(f"/api/boards/{board.id}/columns", json={"order": 5})
    assert response.status_code == 422


def test_rename_column_member_ok(member_client, column):
    response = member_client.patch(f"/api/columns/{column.id}", json={"name": "Renamed"})
    assert response.status_code == 200
    assert response.get_json()["name"] == "Renamed"


def test_member_cannot_set_done(member_client, column):
    response = member_client.patch(f"/api/columns/{column.id}", json={"is_done": True})
    assert response.status_code == 403


def test_admin_sets_done_column(admin_client, column):
    response = admin_client.patch(f"/api/columns/{column.id}", json={"is_done": True})
    assert response.status_code == 200
    assert response.get_json()["is_done"] is True


def test_second_done_column_is_409(admin_client, board, column, make_column):
    other = make_column(board, is_done=False)
    assert admin_client.patch(f"/api/columns/{column.id}", json={"is_done": True}).status_code == 200
    response = admin_client.patch(f"/api/columns/{other.id}", json={"is_done": True})
    assert response.status_code == 409
    assert error_code(response) == "CONFLICT"


def test_unsetting_done_clears_completed_at(admin_client, board, make_column, make_card, people):
    from datetime import datetime, timezone

    done = make_column(board, is_done=True)
    card = make_card(done, people["admin"], completed_at=datetime.now(timezone.utc))
    response = admin_client.patch(f"/api/columns/{done.id}", json={"is_done": False})
    assert response.status_code == 200
    db.session.refresh(card)
    assert card.completed_at is None


def test_patch_column_missing_body_is_422(member_client, column):
    assert member_client.patch(f"/api/columns/{column.id}", json={}).status_code == 422


def test_patch_column_anonymous_is_401(anonymous_client, column):
    assert anonymous_client.patch(f"/api/columns/{column.id}", json={"name": "x"}).status_code == 401


def test_delete_column_member_non_creator_is_403(member_client, board, column, make_column, people):
    owned_by_admin = make_column(board, creator=people["admin"])
    response = member_client.delete(f"/api/columns/{owned_by_admin.id}")
    assert response.status_code == 403


def test_delete_column_member_creator_with_own_cards_is_204(
    member_client, board, people, make_column, make_card
):
    mine = make_column(board, creator=people["member"])
    make_card(mine, people["member"])
    response = member_client.delete(f"/api/columns/{mine.id}")
    assert response.status_code == 204


def test_delete_column_member_creator_with_foreign_card_is_409(
    member_client, board, people, make_column, make_card
):
    mine = make_column(board, creator=people["member"])
    make_card(mine, people["member"])
    make_card(mine, people["other_member"])
    response = member_client.delete(f"/api/columns/{mine.id}")
    assert response.status_code == 409
    assert error_code(response) == "COLUMN_HAS_FOREIGN_WORK"
    assert response.get_json()["error"]["details"] == {"cards": 1}


def test_delete_column_ignores_soft_deleted_foreign_card(
    member_client, board, people, make_column, make_card
):
    mine = make_column(board, creator=people["member"])
    gone = make_card(mine, people["other_member"])
    gone.soft_delete()
    db.session.commit()
    response = member_client.delete(f"/api/columns/{mine.id}")
    assert response.status_code == 204


def test_delete_column_admin_cascades_all_cards(admin_client, board, column, make_card, people):
    make_card(column, people["member"])
    gone = make_card(column, people["member"])
    gone.soft_delete()
    db.session.commit()
    response = admin_client.delete(f"/api/columns/{column.id}")
    assert response.status_code == 204
    assert db.session.get(BoardColumn, column.id) is None
    assert db.session.query(Card).filter(Card.column_id == column.id).count() == 0


def test_delete_column_guest_is_403_and_anonymous_401(guest_client, anonymous_client, column):
    assert guest_client.delete(f"/api/columns/{column.id}").status_code == 403
    assert anonymous_client.delete(f"/api/columns/{column.id}").status_code == 401


def test_reorder_column_moves_and_returns_siblings_only_on_rebalance(member_client, board, column, make_column):
    second = make_column(board, order=2048.0)
    response = member_client.patch(
        f"/api/boards/{board.id}/columns/reorder",
        json={"column_id": str(second.id), "order": 512.0},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["order"] == 512.0
    assert body["rebalanced"] is False and body["siblings"] == []


def test_reorder_column_tie_triggers_rebalance(member_client, board, column, make_column):
    second = make_column(board, order=2048.0)
    response = member_client.patch(
        f"/api/boards/{board.id}/columns/reorder",
        json={"column_id": str(second.id), "order": 1024.0},
    )
    body = response.get_json()
    assert body["rebalanced"] is True
    assert sorted(s["order"] for s in body["siblings"]) == [1024.0, 2048.0]


def test_reorder_column_from_other_board_is_404(member_client, board, outside_board, make_column):
    foreign = make_column(outside_board)
    response = member_client.patch(
        f"/api/boards/{board.id}/columns/reorder",
        json={"column_id": str(foreign.id), "order": 1.0},
    )
    assert response.status_code == 404


def test_reorder_column_non_positive_order_is_422(member_client, board, column):
    response = member_client.patch(
        f"/api/boards/{board.id}/columns/reorder",
        json={"column_id": str(column.id), "order": 0},
    )
    assert response.status_code == 422
