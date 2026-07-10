import json
from flask_login import current_user
from app import db
from app.models import AuditLog

def log_action(action, target_type=None, target_id=None, old_value=None, new_value=None):
    if not current_user or not current_user.is_authenticated:
        return
    entry = AuditLog(
        user_id=current_user.id,
        role=current_user.role,
        action=action,
        target_type=target_type,
        target_id=target_id,
        old_value=json.dumps(old_value) if old_value is not None and not isinstance(old_value, str) else str(old_value) if old_value is not None else None,
        new_value=json.dumps(new_value) if new_value is not None and not isinstance(new_value, str) else str(new_value) if new_value is not None else None,
    )
    db.session.add(entry)
    db.session.flush()
