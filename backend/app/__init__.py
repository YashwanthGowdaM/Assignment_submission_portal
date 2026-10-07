import os
import logging
from datetime import datetime

from flask import Flask
from prometheus_flask_exporter import PrometheusMetrics

from config import config_by_name
from app.extensions import db, migrate, login_manager, csrf, init_redis
from app.utilities.helpers import format_datetime, status_badge_class
from app.utilities.errors import register_error_handlers
from app.routes import auth_bp, admin_bp, student_bp, main_bp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app(config_name=None) -> Flask:
    """Application factory for Assignment Group Portal."""

    if not config_name:
        config_name = os.getenv("FLASK_ENV", "development").lower()

    app = Flask(
        __name__,
        template_folder="/frontend/templates",
        static_folder="/frontend/static",
    )

    config_class = config_by_name.get(config_name, config_by_name["default"])
    app.config.from_object(config_class)

    # ----------------------------------------------------
    # Prometheus Metrics
    # ----------------------------------------------------
    metrics = PrometheusMetrics(app)

    metrics.info(
        "assignment_portal",
        "Assignment Group Portal",
        version="1.0.0",
    )

    # ----------------------------------------------------
    # Initialize Extensions
    # ----------------------------------------------------
    db.init_app(app)
    migrate.init_app(app, db, directory="database/migrations")
    login_manager.init_app(app)
    csrf.init_app(app)

    # Initialize Redis
    with app.app_context():
        init_redis(app)

    # ----------------------------------------------------
    # Template Filters
    # ----------------------------------------------------
    app.jinja_env.filters["datetime"] = format_datetime
    app.jinja_env.filters["status_badge"] = status_badge_class

    # ----------------------------------------------------
    # Global Variables
    # ----------------------------------------------------
    @app.context_processor
    def inject_global_vars():
        return {
            "app_name": app.config.get("APP_NAME", "Assignment Group Portal"),
            "current_year": datetime.now().year,
        }

    # ----------------------------------------------------
    # Error Handlers
    # ----------------------------------------------------
    register_error_handlers(app)

    # ----------------------------------------------------
    # Blueprints
    # ----------------------------------------------------
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(student_bp)

    logger.info(
        f"Initialized {app.config.get('APP_NAME')} with config '{config_name}'"
    )

    return app
