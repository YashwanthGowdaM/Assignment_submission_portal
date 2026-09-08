import logging
import redis
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

logger = logging.getLogger(__name__)

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()

login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "warning"

# Redis client placeholder
redis_client = None


def init_redis(app):
    """
    Initializes Redis client with connection pooling and graceful error handling.
    If Redis is unreachable, sets redis_client to a safe fallback dummy.
    """
    global redis_client
    redis_url = app.config.get("REDIS_URL", "redis://localhost:6379/0")

    try:
        client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_timeout=2.0,
            socket_connect_timeout=2.0,
        )
        # Test ping to ensure connection works
        client.ping()
        redis_client = client
        logger.info(f"Connected to Redis successfully at {redis_url}")
    except Exception as exc:
        logger.warning(
            f"Redis connection failed ({exc}). Falling back to in-memory/mock cache for non-fatal execution."
        )
        redis_client = MockRedisClient()


class MockRedisClient:
    """Fallback in-memory dictionary-based mock when local Redis server is not running."""

    def __init__(self):
        self._store = {}

    def ping(self):
        return True

    def get(self, key):
        return self._store.get(key)

    def set(self, key, value, ex=None):
        self._store[key] = value
        return True

    def setex(self, key, time, value):
        self._store[key] = value
        return True

    def delete(self, *keys):
        count = 0
        for k in keys:
            if k in self._store:
                del self._store[k]
                count += 1
        return count

    def keys(self, pattern="*"):
        import fnmatch
        return fnmatch.filter(self._store.keys(), pattern)

    def flushdb(self):
        self._store.clear()
        return True
