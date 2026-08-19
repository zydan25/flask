import json
import time

from flask import request
from werkzeug.security import check_password_hash

from ..extensions import db, sock
from ..models import Application, RuntimeEvent


def _authorized(app):
    token = (
        request.args.get('token')
        or request.headers.get('X-Runtime-Key')
        or request.headers.get('Authorization', '').removeprefix('Bearer ').strip()
    )
    if not app.runtime_key_hash:
        return True
    return bool(token and check_password_hash(app.runtime_key_hash, token))


@sock.route('/runtime/events/ws')
def events_ws(ws):
    app = Application.query.filter_by(
        slug=request.args.get('app', 'flutter-app'), active=True
    ).first()
    if not app:
        ws.send(json.dumps({'type': 'error', 'error': 'application_not_found'}))
        return
    if not _authorized(app):
        ws.send(json.dumps({'type': 'error', 'error': 'unauthorized'}))
        return

    while True:
        rows = (
            RuntimeEvent.query.filter_by(
                application_id=app.id, acknowledged=False
            )
            .order_by(RuntimeEvent.id.asc())
            .limit(20)
            .all()
        )
        for event in rows:
            ws.send(
                json.dumps(
                    {
                        'event_id': event.event_id,
                        'type': event.event_type,
                        'payload': event.payload_json or {},
                    },
                    ensure_ascii=False,
                )
            )

        try:
            message = ws.receive()
        except Exception:
            message = None
        if message:
            try:
                data = json.loads(message)
                if data.get('type') == 'ack' and data.get('event_ids'):
                    RuntimeEvent.query.filter(
                        RuntimeEvent.event_id.in_(data['event_ids'])
                    ).update(
                        {'acknowledged': True},
                        synchronize_session=False,
                    )
                    db.session.commit()
            except (TypeError, ValueError):
                pass
        time.sleep(2)
