"""Row factories for database tests. Each one flushes, so later rows can reference it.

They set only the columns the test needs. Everything else comes from the schema
defaults, which is what the tests check.
"""

import uuid


def new_user(sess, name="Tester", email=None):
    from app.models import User

    user = User(
        name=name,
        email=email or f"{uuid.uuid4().hex}@example.com",
        password_hash="hash",
    )
    sess.add(user)
    sess.flush()
    return user


def new_board(sess, creator=None, name="Board", is_public=None):
    from app.models import Board

    kwargs = {"name": name, "created_by": creator.id if creator else None}
    if is_public is not None:
        kwargs["is_public"] = is_public
    board = Board(**kwargs)
    sess.add(board)
    sess.flush()
    return board


def new_member(sess, board, user, role="member", added_by=None):
    from app.models import BoardMember

    member = BoardMember(
        board_id=board.id,
        user_id=user.id,
        role=role,
        added_by=added_by.id if added_by else None,
    )
    sess.add(member)
    sess.flush()
    return member


def new_column(sess, board, name="To Do", position=1.0, is_done=False, creator=None):
    from app.models import BoardColumn

    column = BoardColumn(
        board_id=board.id,
        name=name,
        order=position,
        is_done=is_done,
        created_by=creator.id if creator else None,
    )
    sess.add(column)
    sess.flush()
    return column


def new_card(sess, column, title="Card", position=1.0, creator=None, assignee=None):
    """`board_id` is copied from the column, as the service layer does (DB-SCH-03)."""
    from app.models import Card

    card = Card(
        board_id=column.board_id,
        column_id=column.id,
        title=title,
        order=position,
        created_by=creator.id if creator else None,
        assignee_id=assignee.id if assignee else None,
    )
    sess.add(card)
    sess.flush()
    return card


def new_comment(sess, card, content="Looks good", creator=None):
    from app.models import Comment

    comment = Comment(
        card_id=card.id,
        content=content,
        created_by=creator.id if creator else None,
    )
    sess.add(comment)
    sess.flush()
    return comment
