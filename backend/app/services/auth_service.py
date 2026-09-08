import secrets
from app.extensions import db
from app.models.user import User
from app.models.audit_log import AuditLog


class AuthService:
    """Service handling user credentials, registration, and password recovery tokens."""

    # In-memory or Redis token store for password recovery simulation
    _reset_tokens = {}

    @classmethod
    def register_student(cls, full_name: str, email: str, password: str, student_id: str = None) -> User:
        user = User(
            full_name=full_name.strip(),
            email=email.strip().lower(),
            student_id=student_id.strip() if student_id else None,
            role=User.ROLE_STUDENT,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        AuditLog.log(
            action="USER_REGISTERED",
            entity_type="user",
            entity_id=user.id,
            details=f"New student {user.full_name} ({user.email}) registered.",
            user_id=user.id,
        )
        return user

    @classmethod
    def generate_password_reset_token(cls, user: User) -> str:
        token = secrets.token_urlsafe(32)
        cls._reset_tokens[token] = user.id
        return token

    @classmethod
    def verify_password_reset_token(cls, token: str) -> User | None:
        user_id = cls._reset_tokens.get(token)
        if user_id:
            return db.session.get(User, user_id)
        return None

    @classmethod
    def consume_password_reset_token(cls, token: str, new_password: str) -> bool:
        user = cls.verify_password_reset_token(token)
        if not user:
            return False
        user.set_password(new_password)
        db.session.commit()
        cls._reset_tokens.pop(token, None)
        return True
