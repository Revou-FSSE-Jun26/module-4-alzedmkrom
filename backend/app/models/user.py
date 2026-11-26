from app.extensions import db
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "users"

    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    # Salted hash only. There is no plaintext password column.
    password_hash = db.Column(db.String(255), nullable=False)

    __table_args__ = (
        # Minimum-length checks per OD-3. Maximum lengths come from VARCHAR.
        db.CheckConstraint("char_length(name) >= 1", name="name_length"),
        db.CheckConstraint("char_length(email) BETWEEN 3 AND 254", name="email_length"),
        db.CheckConstraint(
            "char_length(password_hash) >= 1", name="password_hash_length"
        ),
        db.Index("uq_users_email_lower", db.func.lower(email), unique=True),
    )

    def __repr__(self) -> str:
        return f"<User {self.id}>"
