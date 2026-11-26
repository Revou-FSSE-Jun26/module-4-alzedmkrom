"""Card endpoints, moves and ordering, soft delete, assigned tasks (BE-TST-02, BE-TST-03, BE-SVC-06)."""
from datetime import datetime, timezone

from app.extensions import db
from app.models import Card, Notification
from tests.api.conftest import error_code


def test_create_card_appends_and_sets_creator(member_client, column, people):
    response = member_client.post(f"/api/columns/{column.id}/cards", json={"title": "Fix login"})
    assert response.status_code == 201
    body = response.get_json()
    assert body["order"] == 1024.0
    assert body["created_by"] == str(people["member"].id)
    assert body["completed_at"] is None


def test_create_card_in_done_column_sets_completed_at(admin_client, board, make_column):
    done = make_column(board, is_done=True)
    response = admin_client.post(f"/api/columns/{done.id}/cards", json={"title": "Already done"})
    assert response.status_code == 201
    assert response.get_json()["completed_at"].endswith("Z")


def test_create_card_with_assignee_notifies_assignee(member_client, column, people):
    response = member_client.post(
        f"/api/columns/{column.id}/cards",
        json={"title": "Pass it on", "assignee_id": str(people["other_member"].id)},
    )
    assert response.status_code == 201
    rows = db.session.query(Notification).filter_by(user_id=people["other_member"].id).all()
    assert [r.type for r in rows] == ["card_assigned"]


def test_create_card_assignee_not_member_is_422(member_client, column, people):
    response = member_client.post(
        f"/api/columns/{column.id}/cards",
        json={"title": "Outsider", "assignee_id": str(people["guest"].id)},
    )
    assert response.status_code == 422
    assert response.get_json()["error"]["details"] == {
        "assignee_id": ["User is not a member of this board."]
    }


def test_create_card_guest_403_anonymous_401(guest_client, anonymous_client, column):
    assert guest_client.post(f"/api/columns/{column.id}/cards", json={"title": "x"}).status_code == 403
    assert anonymous_client.post(f"/api/columns/{column.id}/cards", json={"title": "x"}).status_code == 401


def test_create_card_missing_title_is_422(member_client, column):
    response = member_client.post(f"/api/columns/{column.id}/cards", json={"description": "x"})
    assert response.status_code == 422


def test_create_card_rejects_client_order(member_client, column):
    response = member_client.post(
        f"/api/columns/{column.id}/cards", json={"title": "x", "order": 5}
    )
    assert response.status_code == 422


def test_create_card_description_over_limit_is_422(member_client, column):
    response = member_client.post(
        f"/api/columns/{column.id}/cards", json={"title": "x", "description": "d" * 5001}
    )
    assert response.status_code == 422


def test_update_card_member_ok(member_client, column, make_card, people):
    card = make_card(column, people["member"])
    response = member_client.patch(f"/api/cards/{card.id}", json={"title": "New title", "due_date": "2030-01-02"})
    assert response.status_code == 200
    body = response.get_json()
    assert body["title"] == "New title" and body["due_date"] == "2030-01-02"


def test_update_card_empty_body_is_422(member_client, column, make_card, people):
    card = make_card(column, people["member"])
    assert member_client.patch(f"/api/cards/{card.id}", json={}).status_code == 422


def test_update_card_assignee_change_notifies_new_assignee(member_client, column, make_card, people):
    card = make_card(column, people["member"])
    member_client.patch(f"/api/cards/{card.id}", json={"assignee_id": str(people["other_member"].id)})
    types = [n.type for n in db.session.query(Notification).filter_by(user_id=people["other_member"].id)]
    assert types == ["card_assigned"]


def test_update_card_soft_deleted_is_404(member_client, column, make_card, people):
    card = make_card(column, people["member"])
    card.soft_delete()
    db.session.commit()
    assert member_client.patch(f"/api/cards/{card.id}", json={"title": "x"}).status_code == 404


def test_move_card_between_columns(member_client, board, column, make_column, make_card, people):
    target = make_column(board, order=2048.0)
    card = make_card(column, people["member"])
    response = member_client.patch(
        f"/api/cards/{card.id}/position", json={"column_id": str(target.id), "order": 512.0}
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["column_id"] == str(target.id)
    assert body["order"] == 512.0
    assert body["rebalanced"] is False and body["siblings"] == []


def test_move_card_order_zero_is_422(member_client, column, make_card, people):
    card = make_card(column, people["member"])
    response = member_client.patch(
        f"/api/cards/{card.id}/position", json={"column_id": str(column.id), "order": 0}
    )
    assert response.status_code == 422


def test_move_card_no_token_is_401(anonymous_client, column, make_card, people):
    card = make_card(column, people["member"])
    response = anonymous_client.patch(
        f"/api/cards/{card.id}/position", json={"column_id": str(column.id), "order": 5}
    )
    assert response.status_code == 401


def test_move_card_to_other_board_column_is_422(member_client, column, outside_board, make_column, make_card, people):
    foreign = make_column(outside_board)
    card = make_card(column, people["member"])
    response = member_client.patch(
        f"/api/cards/{card.id}/position", json={"column_id": str(foreign.id), "order": 5}
    )
    assert response.status_code == 422
    assert response.get_json()["error"]["details"] == {
        "column_id": ["Column belongs to a different board."]
    }


def test_move_card_tie_rebalances_column(member_client, column, make_card, people):
    first = make_card(column, people["member"], order=1024.0)
    second = make_card(column, people["member"], order=2048.0)
    mover = make_card(column, people["member"], order=3072.0)
    response = member_client.patch(
        f"/api/cards/{mover.id}/position", json={"column_id": str(column.id), "order": 1024.0}
    )
    body = response.get_json()
    assert body["rebalanced"] is True
    numbered = sorted(s["order"] for s in body["siblings"])
    assert numbered == [1024.0, 2048.0, 3072.0]
    db.session.refresh(first)
    db.session.refresh(second)
    assert first.order == 2048.0 or first.order == 1024.0
    assert {first.order, second.order, mover.order} == {1024.0, 2048.0, 3072.0}


def test_move_into_done_column_sets_completed_at_and_out_clears_it(
    admin_client, board, column, make_column, make_card, people
):
    done = make_column(board, is_done=True)
    card = make_card(column, people["member"])
    moved = admin_client.patch(
        f"/api/cards/{card.id}/position", json={"column_id": str(done.id), "order": 100.0}
    ).get_json()
    assert moved["completed_at"].endswith("Z")
    back = admin_client.patch(
        f"/api/cards/{card.id}/position", json={"column_id": str(column.id), "order": 100.0}
    ).get_json()
    assert back["completed_at"] is None


def test_move_to_other_column_notifies_admins_not_actor(
    member_client, admin_client, board, column, make_column, make_card, people
):
    target = make_column(board, order=2048.0)
    card = make_card(column, people["member"])
    member_client.patch(
        f"/api/cards/{card.id}/position", json={"column_id": str(target.id), "order": 50.0}
    )
    admin_rows = db.session.query(Notification).filter_by(user_id=people["admin"].id, type="card_moved").all()
    member_rows = db.session.query(Notification).filter_by(user_id=people["member"].id).all()
    assert len(admin_rows) == 1
    assert member_rows == []


def test_move_within_same_column_creates_no_notification(member_client, column, make_card, people):
    card = make_card(column, people["member"], order=1024.0)
    member_client.patch(f"/api/cards/{card.id}/position", json={"column_id": str(column.id), "order": 2000.0})
    assert db.session.query(Notification).count() == 0


def test_delete_card_member_creator_is_soft_delete_204(member_client, column, make_card, people):
    card = make_card(column, people["member"])
    response = member_client.delete(f"/api/cards/{card.id}")
    assert response.status_code == 204
    row = db.session.get(Card, card.id)
    assert row is not None and row.deleted_at is not None


def test_delete_card_member_creator_with_others_comment_is_204(
    member_client, column, make_card, make_comment, people
):
    card = make_card(column, people["member"])
    make_comment(card, people["other_member"])
    assert member_client.delete(f"/api/cards/{card.id}").status_code == 204


def test_delete_card_member_non_creator_is_403(other_member_client, column, make_card, people):
    card = make_card(column, people["member"])
    assert other_member_client.delete(f"/api/cards/{card.id}").status_code == 403


def test_delete_card_admin_any_is_204(admin_client, column, make_card, people):
    card = make_card(column, people["member"])
    assert admin_client.delete(f"/api/cards/{card.id}").status_code == 204


def test_delete_card_guest_403_anonymous_401(guest_client, anonymous_client, column, make_card, people):
    card = make_card(column, people["member"])
    assert guest_client.delete(f"/api/cards/{card.id}").status_code == 403
    assert anonymous_client.delete(f"/api/cards/{card.id}").status_code == 401


def test_soft_deleted_card_comments_return_404(member_client, column, make_card, make_comment, people):
    card = make_card(column, people["member"])
    make_comment(card, people["member"])
    member_client.delete(f"/api/cards/{card.id}")
    response = member_client.get(f"/api/cards/{card.id}/comments")
    assert response.status_code == 404


def test_assigned_cards_requires_assignee_me(member_client):
    assert member_client.get("/api/cards").status_code == 422
    assert member_client.get("/api/cards?assignee=someone").status_code == 422


def test_assigned_cards_requires_token(anonymous_client):
    assert anonymous_client.get("/api/cards?assignee=me").status_code == 401


def test_assigned_cards_lists_own_live_cards(member_client, column, make_card, people):
    mine = make_card(column, people["admin"], assignee=people["member"])
    gone = make_card(column, people["admin"], assignee=people["member"])
    gone.soft_delete()
    db.session.commit()
    response = member_client.get("/api/cards?assignee=me")
    assert response.status_code == 200
    body = response.get_json()
    assert [item["id"] for item in body["items"]] == [str(mine.id)]
    assert body["items"][0]["board_name"] == "Team board"
    assert body["items"][0]["column_name"] == column.name


def test_assigned_cards_excludes_boards_user_left(
    member_client, admin_client, column, make_card, people
):
    make_card(column, people["admin"], assignee=people["member"])
    admin_client.delete(f"/api/boards/{column.board_id}/members/{people['member'].id}")
    response = member_client.get("/api/cards?assignee=me")
    assert response.get_json()["items"] == []


def test_assigned_cards_done_filter(member_client, column, make_card, people):
    make_card(column, people["admin"], assignee=people["member"])
    make_card(column, people["admin"], assignee=people["member"], completed_at=datetime.now(timezone.utc))
    response = member_client.get("/api/cards?assignee=me&done=true")
    assert len(response.get_json()["items"]) == 1
