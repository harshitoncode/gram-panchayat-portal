from db import get_db


def create_notification(user_id, message, link=None):
    """Insert a notification for the given user."""
    db = get_db()
    db.execute(
        'INSERT INTO notifications (user_id, message, link) VALUES (?, ?, ?)',
        (user_id, message, link),
    )
    db.commit()
