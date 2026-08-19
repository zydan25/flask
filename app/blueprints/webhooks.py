from uuid import uuid4
from flask import Blueprint,jsonify,request
from ..extensions import db
from ..models import RuntimeEvent
from ..services.runtime_service import get_application
bp=Blueprint('webhooks',__name__,url_prefix='/hooks')
@bp.post('/<app_slug>/<hook_name>')
def inbound(app_slug,hook_name):
    app=get_application(app_slug)
    if not app:return jsonify(error='application_not_found'),404
    payload=request.get_json(silent=True)
    if payload is None:payload={'raw':request.get_data(as_text=True)}
    event=RuntimeEvent(application_id=app.id,event_id=str(uuid4()),event_type=hook_name,payload_json=payload); db.session.add(event); db.session.commit(); return jsonify(ok=True,event_id=event.event_id)
