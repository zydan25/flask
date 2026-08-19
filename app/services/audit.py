from flask_login import current_user
from ..extensions import db
from ..models import AuditLog

def audit(action, resource_type, resource_id=None, payload=None):
    db.session.add(AuditLog(action=action,resource_type=resource_type,resource_id=str(resource_id) if resource_id is not None else None,payload_json=payload or {},user_id=current_user.id if getattr(current_user,'is_authenticated',False) else None))
