"""Comments, notifications and analytics (BE-TST-02, BE-AZ-02, BE-NTF-02, BE-NTF-03, BE-ANL-01)."""
from app.extensions import db
from app.models import Comment, Notification
from tests.api.conftest import error_code


def test_list_comments_anonymous_on_public_board(anonymous_client, column, make_card, make_comment, people):
    card = make_card(column, people["member"])
    make_comment(card, people["member"], "first")
    make_comment(card, people["other_member"], "second")
    response = anonymous_client.get(f"/api/cards/{card.id}/comments")
    assert response.status_code == 200
    items = response.get_json()["items"]
    assert [i["content"] for i in items] == ["first", "second"]
    assert items[0]["author"] == {"id": str(people["member"].id), "name": people["member"].name}


def test_list_comments_private_board_anonymous_is_404(anonymous_client, private_board, make_column, make_card, people):
    card = make_card(make_column(private_board), people["member"])
    assert anonymous_client.get(f"/api/cards/{card.id}/comments").status_code == 404


def test_create_comment_member_201_and_notifies_assignee(member_client, column, make_card, people):
    card = make_card(column, people["admin"], assignee=people["other_member"])
    response = member_client.post(f"/api/cards/{card.id}/comments", json={"content": "Looks good"})
    assert response.status_code == 201
    assert response.get_json()["content"] == "Looks good"
    types = [n.type for n in db.session.query(Notification).filter_by(user_id=people["other_member"].id)]
    assert types == ["comment_added"]


def test_create_comment_assignee_commenting_on_own_card_is_not_notified(
    member_client, column, make_card, people
):
    card = make_card(column, people["admin"], assignee=people["member"])
    member_client.post(f"/api/cards/{card.id}/comments", json={"content": "me"})
    assert db.session.query(Notification).count() == 0


def test_create_comment_empty_is_422(member_client, column, make_card, people):
    card = make_card(column, people["member"])
    assert member_client.post(f"/api/cards/{card.id}/comments", json={"content": "   "}).status_code == 422


def test_create_comment_guest_403_anonymous_401(guest_client, anonymous_client, column, make_card, people):
    card = make_card(column, people["member"])
    assert guest_client.post(f"/api/cards/{card.id}/comments", json={"content": "x"}).status_code == 403
    assert anonymous_client.post(f"/api/cards/{card.id}/comments", json={"content": "x"}).status_code == 401


def test_edit_own_comment_ok(member_client, column, make_card, make_comment, people):
    card = make_card(column, people["member"])
    comment = make_comment(card, people["member"], "old")
    response = member_client.patch(f"/api/comments/{comment.id}", json={"content": "new"})
    assert response.status_code == 200
    assert response.get_json()["content"] == "new"


def test_admin_cannot_edit_or_delete_others_comment(admin_client, column, make_card, make_comment, people):
    card = make_card(column, people["member"])
    comment = make_comment(card, people["member"])
    assert admin_client.patch(f"/api/comments/{comment.id}", json={"content": "x"}).status_code == 403
    assert admin_client.delete(f"/api/comments/{comment.id}").status_code == 403


def test_delete_own_comment_204(member_client, column, make_card, make_comment, people):
    card = make_card(column, people["member"])
    comment = make_comment(card, people["member"])
    assert member_client.delete(f"/api/comments/{comment.id}").status_code == 204
    assert db.session.get(Comment, comment.id) is None


def test_comment_change_requires_membership(guest_client, column, make_card, make_comment, people, make_board):
    card = make_card(column, people["member"])
    comment = make_comment(card, people["member"])
    response = guest_client.patch(f"/api/comments/{comment.id}", json={"content": "x"})
    assert response.status_code == 403


def test_comment_change_anonymous_is_401(anonymous_client, column, make_card, make_comment, people):
    card = make_card(column, people["member"])
    comment = make_comment(card, people["member"])
    assert anonymous_client.delete(f"/api/comments/{comment.id}").status_code == 401


def test_notifications_list_with_unread_count(member_client, board, make_notification, people):
    make_notification(people["member"], board)
    read = make_notification(people["member"], board)
    read.is_read = True
    db.session.commit()
    response = member_client.get("/api/notifications?page=1&per_page=10")
    assert response.status_code == 200
    body = response.get_json()
    assert body["total"] == 2 and body["unread_count"] == 1 and body["pages"] == 1
    assert set(body["items"][0]) == {"id", "type", "message", "board_id", "is_read", "created_at"}


def test_notifications_out_of_range_per_page_is_422(member_client):
    assert member_client.get("/api/notifications?per_page=101").status_code == 422


def test_notifications_requires_token(anonymous_client):
    assert anonymous_client.get("/api/notifications").status_code == 401


def test_mark_read_is_idempotent(member_client, board, make_notification, people):
    note = make_notification(people["member"], board)
    for _ in range(2):
        response = member_client.patch(f"/api/notifications/{note.id}/read")
        assert response.status_code == 200
        assert response.get_json()["is_read"] is True


def test_mark_read_someone_elses_is_404(other_member_client, board, make_notification, people):
    note = make_notification(people["member"], board)
    assert other_member_client.patch(f"/api/notifications/{note.id}/read").status_code == 404


def test_analytics_admin_shape(admin_client, board, column, make_card, make_comment, people):
    card = make_card(column, people["member"], assignee=people["member"])
    make_comment(card, people["member"])
    response = admin_client.get(f"/api/boards/{board.id}/analytics")
    assert response.status_code == 200
    body = response.get_json()
    assert body["week_start"].endswith("Z")
    assert body["cards_per_column"] == [
        {"column_id": str(column.id), "name": column.name, "total_cards": 1}
    ]
    assert body["completed_this_week"] == 0
    activity = {m["name"]: m for m in body["member_activity"]}
    assert activity[people["member"].name]["cards_created"] == 1
    assert activity[people["member"].name]["comments_added"] == 1
    assert activity[people["member"].name]["cards_assigned"] == 1
    assert activity[people["member"].name]["assigned_cards_completed_this_week"] == 0
    assert people["outside_admin"].name not in activity


def test_analytics_member_and_guest_are_403(member_client, guest_client, board):
    assert member_client.get(f"/api/boards/{board.id}/analytics").status_code == 403
    assert guest_client.get(f"/api/boards/{board.id}/analytics").status_code == 403


def test_analytics_private_non_member_is_404(outside_admin_client, private_board):
    assert outside_admin_client.get(f"/api/boards/{private_board.id}/analytics").status_code == 404


def test_analytics_anonymous_is_401(anonymous_client, board):
    response = anonymous_client.get(f"/api/boards/{board.id}/analytics")
    assert response.status_code == 401
    assert error_code(response) == "UNAUTHENTICATED"
