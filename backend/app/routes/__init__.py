from app.routes.auth import auth_bp
from app.routes.admin import admin_bp
from app.routes.student import student_bp
from app.routes.main import main_bp

__all__ = ["auth_bp", "admin_bp", "student_bp", "main_bp"]
