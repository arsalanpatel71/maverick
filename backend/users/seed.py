import logging

from auth.service import hash_password
from settings import get_settings
from users.store import UserStore

logger = logging.getLogger(__name__)


def seed_super_admin() -> None:
    settings = get_settings()
    email = settings.super_admin_email
    password = settings.super_admin_password
    if not email or not password:
        logger.warning("SUPER_ADMIN_EMAIL or SUPER_ADMIN_PASSWORD not set in .env — skipping seed")
        return
    store = UserStore()
    if store.get_by_email(email):
        return
    store.create(
        email=email,
        name="Super Admin",
        password_hash=hash_password(password),
        role="super_admin",
        credits_limit=999999.0,
    )
    logger.info("Seeded super admin: %s", email)
