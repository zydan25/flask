import json,time
from flask import request
from ..extensions import sock,db
from ..models import Application,RuntimeEvent
@sock.route('/runtime/events/ws')
def events_ws(ws):
    app=Application.query.filter_by(slug=request.args.get('app','flutter-app'),active=True).first()
    if not app: ws.send(json.dumps({'type':'error','error':'application_not_found'})); return
    while True:
        rows=RuntimeEvent.query.filter_by(application_id=app.id,acknowledged=False).order_by(RuntimeEvent.id.asc()).limit(20).all()
        for event in rows: ws.send(json.dumps({'event_id':event.event_id,'type':event.event_type,'payload':event.payload_json or {}},ensure_ascii=False))
        try: message=ws.receive()
        except Exception: message=None
        if message:
            try:
                data=json.loads(message)
                if data.get('type')=='ack' and data.get('event_ids'):
                    RuntimeEvent.query.filter(RuntimeEvent.event_id.in_(data['event_ids'])).update({'acknowledged':True},synchronize_session=False); db.session.commit()
            except Exception: pass
        time.sleep(2)
