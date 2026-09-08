from flask import Blueprint, redirect, url_for, jsonify
from flask_login import current_user

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("student.dashboard"))
    return redirect(url_for("auth.login"))


@main_bp.route("/health")
def health():
    return jsonify({"status": "healthy", "service": "assignment-group-portal"})
