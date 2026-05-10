"""middlewares/auth.py — admin check and rate limiting"""
import time
import logging
from collections import defaultdict
from config.settings import ADMIN_IDS

logger = logging.getLogger(__name__)

# Simple in-memory rate limiter: {user_id: [timestamps]}
_message_times: dict[int, list[float]] = defaultdict(list)
RATE_LIMIT = 30   # max messages
RATE_WINDOW = 60  # per 60 seconds


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def is_rate_limited(user_id: int) -> bool:
    """Returns True if user is sending too many messages."""
    if is_admin(user_id):
        return False  # admins are never rate-limited
    now = time.time()
    times = _message_times[user_id]
    # Remove timestamps outside the window
    _message_times[user_id] = [t for t in times if now - t < RATE_WINDOW]
    if len(_message_times[user_id]) >= RATE_LIMIT:
        logger.warning(f"Rate limit hit: user {user_id}")
        return True
    _message_times[user_id].append(now)
    return False
