import pytest
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.assignment import Assignment
from app.models.group import Group, GroupMember
from app.models.submission import Submission
from app.models.audit_log import AuditLog
from config import TestingConfig


@pytest.fixture(scope="session")
def app():
    """Create and configure a clean Flask app for testing."""
    app = create_app(TestingConfig)
    return app


@pytest.fixture(scope="function")
def client(app):
    """A test client for the app with a fresh isolated DB per test."""
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


@pytest.fixture
def admin_user(app):
    """Seed and return a verified Admin user."""
    with app.app_context():
        admin = User(
            email="admin@test.edu",
            full_name="Dr. Administrator",
            role="admin",
            is_active=True,
        )
        admin.set_password("Admin@12345")
        db.session.add(admin)
        db.session.commit()
        return admin.id


@pytest.fixture
def sample_students(app):
    """Seed and return a list of 4 student user IDs."""
    ids = []
    with app.app_context():
        for i in range(1, 5):
            student = User(
                email=f"student{i}@test.edu",
                full_name=f"Student {i}",
                student_id=f"STU-00{i}",
                role="student",
                is_active=True,
            )
            student.set_password("Student@12345")
            db.session.add(student)
            db.session.commit()
            ids.append(student.id)
    return ids
