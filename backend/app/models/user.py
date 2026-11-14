from app.extensions import db
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "users"

    name = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, nullable=False)
    # Only a hash is stored; there is no plaintext password column.
    password_hash = db.Column(db.Text, nullable=False)

    __table_args__ = (
        db.CheckConstraint("char_length(name) BETWEEN 1 AND 255", name="name_length"),
        db.CheckConstraint("char_length(email) BETWEEN 3 AND 254", name="email_length"),
        db.Index("uq_users_email_lower", db.func.lower(email), unique=True),
    )

    def __repr__(self) -> str:
        return f"<User {self.id}>"
