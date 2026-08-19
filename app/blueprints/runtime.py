from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets

from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash

from ..extensions import db
from ..models import DeviceRegistration, RuntimeEvent, RuntimeRelease, SyncOperation
from ..services.data_service import (
    create_record,
    delete_record,
    get_model,
    list_records,
    serialize_record,
    update_record,
)
from ..services.runtime_service import current_release, get_application

bp = Blueprint('runtime', __name__, url_prefix='/runtime')

_ACCESS_TTL_SECONDS = 900
_REFRESH_TTL_SECONDS = 60 * 60 * 24 * 30


def _auth_state(app):
    state = (app.config_json or {}).get('_runtime_auth') or {}
    return state


def _hash_token(token):
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def _constant_hash_compare(actual, expected):
    return bool(actual and expected and hmac.compare_digest(actual, expected))


def _issue_session(app):
    access_token = secrets.token_urlsafe(32)
    refresh_token = secrets.token_urlsafe(48)
    now = datetime.now(timezone.utc)
    state = {
        'access_hash': _hash_token(access_token),
        'access_expires_at': (now + timedelta(seconds=_ACCESS_TTL_SECONDS)).isoformat(),
        'refresh_hash': _hash_token(refresh_token),
        'refresh_expires_at': (now + timedelta(seconds=_REFRESH_TTL_SECONDS)).isoformat(),
    }
    config = dict(app.config_json or {})
    config['_runtime_auth'] = state
    app.config_json = config
    db.session.add(app)
    db.session.commit()
    return access_token, refresh_token, state


def _access_token_valid(app, token):
    state = _auth_state(app)
    if not state:
        return False
    if not _constant_hash_compare(_hash_token(token), state.get('access_hash')):
        return False
    try:
        expires = datetime.fromisoformat(state['access_expires_at'])
    except (KeyError, ValueError):
        return False
    return datetime.now(timezone.utc) < expires


def authorized(app):
    token = request.headers.get('X-Runtime-Key') or request.headers.get('Authorization', '').removeprefix('Bearer ').strip()
    if not app.runtime_key_hash:
        return True
    if token and check_password_hash(app.runtime_key_hash, token):
        return True
    return bool(token and _access_token_valid(app, token))


def app_or_404():
    return get_application(request.args.get('app', 'flutter-app'))


@bp.get('/health')
def health():
    app = app_or_404()
    if not app:
        return jsonify(status='down', error='application_not_found'), 404
    release = current_release(app)
    return jsonify(
        status='ok',
        app=app.slug,
        runtime_schema=release.schema_version if release else None,
        release=release.version if release else None,
    )


@bp.get('/bootstrap')
def bootstrap():
    app = app_or_404()
    if not app:
        return jsonify(error='application_not_found'), 404
    release = current_release(app)
    if not release:
        return jsonify(error='no_published_release'), 503
    if not authorized(app):
        return jsonify(error='unauthorized'), 401
    return jsonify(
        schema_version=release.schema_version,
        app={'slug': app.slug, 'name': app.name, 'package_name': app.package_name},
        release={'version': release.version, 'checksum': release.checksum, 'published_at': release.published_at.isoformat() if release.published_at else None},
        manifest_url=f'/runtime/manifest?app={app.slug}&version={release.version}',
        resources_url=f'/runtime/resources?app={app.slug}&version={release.version}',
        sync_url=f'/runtime/sync?app={app.slug}',
        events_ack_url='/runtime/events/ack',
        events_ws_url=f'/runtime/events/ws?app={app.slug}',
        client_mode=(app.config_json or {}).get('client_mode', 'server_driven'),
    )


@bp.get('/manifest')
def manifest():
    app = app_or_404()
    if not app:
        return jsonify(error='application_not_found'), 404
    release = current_release(app)
    if not release:
        return jsonify(error='no_published_release'), 503
    if not authorized(app):
        return jsonify(error='unauthorized'), 401
    return jsonify(schema_version=release.schema_version, version=release.version, checksum=release.checksum, **(release.manifest_json or {}))


@bp.get('/resources')
def resources():
    app = app_or_404()
    if not app:
        return jsonify(error='application_not_found'), 404
    release = current_release(app)
    if not release:
        return jsonify(error='no_published_release'), 503
    if not authorized(app):
        return jsonify(error='unauthorized'), 401
    keys = [k for k in request.args.get('keys', '').split(',') if k]
    payload = release.resources_json or {}
    payload = {k: payload[k] for k in keys if k in payload} if keys else payload
    return jsonify(schema_version=release.schema_version, version=release.version, resources=payload)


@bp.post('/auth/refresh')
def refresh_auth():
    data = request.get_json(silent=True) or {}
    app = get_application(data.get('app') or request.args.get('app', 'flutter-app'))
    if not app:
        return jsonify(error='application_not_found'), 404
    refresh_token = str(data.get('refresh_token', '')).strip()
    if not refresh_token:
        return jsonify(error='missing_refresh_token'), 400

    state = _auth_state(app)
    valid = False
    if state:
        try:
            expires = datetime.fromisoformat(state['refresh_expires_at'])
            valid = (
                datetime.now(timezone.utc) < expires
                and _constant_hash_compare(_hash_token(refresh_token), state.get('refresh_hash'))
            )
        except (KeyError, ValueError):
            valid = False

    if not valid:
        # Permit the configured runtime key as the one-time bootstrap credential.
        valid = bool(app.runtime_key_hash and check_password_hash(app.runtime_key_hash, refresh_token))

    if not valid:
        return jsonify(error='invalid_refresh_token'), 401

    access_token, rotated_refresh, state = _issue_session(app)
    return jsonify(
        access_token=access_token,
        refresh_token=rotated_refresh,
        token_type='Bearer',
        expires_in=_ACCESS_TTL_SECONDS,
        refresh_expires_in=_REFRESH_TTL_SECONDS,
    )


@bp.get('/data/<model_slug>')
def data_list(model_slug):
    app = app_or_404()
    if not app:
        return jsonify(error='application_not_found'), 404
    if not authorized(app):
        return jsonify(error='unauthorized'), 401
    model = get_model(app, model_slug)
    if not model:
        return jsonify(error='data_model_not_found'), 404
    try:
        page = max(1, int(request.args.get('page', 1)))
        per_page = min(100, max(1, int(request.args.get('per_page', 25))))
    except ValueError:
        return jsonify(error='invalid_pagination'), 400
    rows, total = list_records(model, page, per_page, request.args.get('include_deleted') == 'true')
    return jsonify(model={'slug': model.slug, 'schema': model.schema_json or {}, 'version': model.updated_at.isoformat() if model.updated_at else None}, data=rows, page=page, per_page=per_page, total=total)


@bp.post('/data/<model_slug>')
def data_create(model_slug):
    app = app_or_404()
    if not app:
        return jsonify(error='application_not_found'), 404
    if not authorized(app):
        return jsonify(error='unauthorized'), 401
    model = get_model(app, model_slug)
    if not model:
        return jsonify(error='data_model_not_found'), 404
    body = request.get_json(silent=True) or {}
    record_key = str(body.get('id') or body.get('key') or '').strip()
    payload = body.get('data')
    if not record_key:
        return jsonify(error='missing_record_key'), 400
    if not isinstance(payload, dict):
        return jsonify(error='invalid_data'), 400
    record, errors, status = create_record(model, record_key, payload)
    if errors:
        return jsonify(error='validation_error', details=errors), 422
    if status == 'exists':
        return jsonify(error='already_exists', record=serialize_record(record)), 409
    return jsonify(record=serialize_record(record)), 201


@bp.route('/data/<model_slug>/<record_key>', methods=['GET', 'PUT', 'PATCH', 'DELETE'])
def data_item(model_slug, record_key):
    app = app_or_404()
    if not app:
        return jsonify(error='application_not_found'), 404
    if not authorized(app):
        return jsonify(error='unauthorized'), 401
    model = get_model(app, model_slug)
    if not model:
        return jsonify(error='data_model_not_found'), 404
    from ..models import DataRecord
    record = DataRecord.query.filter_by(model_id=model.id, record_key=record_key).first()
    if request.method == 'GET':
        if not record or record.deleted:
            return jsonify(error='record_not_found'), 404
        return jsonify(record=serialize_record(record))
    if not record:
        return jsonify(error='record_not_found'), 404
    body = request.get_json(silent=True) or {}
    base_version = request.headers.get('If-Match') or body.get('base_version')
    try:
        base_version = int(base_version) if base_version not in (None, '') else None
    except ValueError:
        return jsonify(error='invalid_base_version'), 400
    if request.method == 'DELETE':
        record, status = delete_record(record, base_version)
        if status == 'conflict':
            return jsonify(error='conflict', server=serialize_record(record)), 409
        return jsonify(record=serialize_record(record))
    payload = body.get('data', body)
    if not isinstance(payload, dict):
        return jsonify(error='invalid_data'), 400
    record, errors, status = update_record(model, record, payload, base_version)
    if errors:
        return jsonify(error='validation_error', details=errors), 422
    if status == 'conflict':
        return jsonify(error='conflict', server=serialize_record(record)), 409
    return jsonify(record=serialize_record(record))


@bp.post('/sync')
def sync():
    data = request.get_json(silent=True) or {}
    app = get_application(data.get('app') or request.args.get('app', 'flutter-app'))
    if not app:
        return jsonify(error='application_not_found'), 404
    if not authorized(app):
        return jsonify(error='unauthorized'), 401
    results = []
    for item in data.get('operations') or []:
        op_id = str(item.get('operation_id', '')).strip()
        if not op_id:
            results.append({'status': 'rejected', 'error': 'missing_operation_id'})
            continue
        existing = SyncOperation.query.filter_by(operation_id=op_id).first()
        if existing:
            results.append({'operation_id': op_id, 'status': existing.status, 'result': existing.result_json or {}, 'server_version': existing.server_version})
            continue
        op = SyncOperation(application_id=app.id, operation_id=op_id, entity=str(item.get('entity', '')), entity_id=str(item.get('entity_id', '')), operation=str(item.get('operation', 'update')), base_version=int(item.get('base_version') or 0), payload_json=item.get('payload') or {}, status='acknowledged', server_version=int(item.get('base_version') or 0) + 1)
        db.session.add(op)
        results.append({'operation_id': op_id, 'status': 'acknowledged', 'server_version': op.server_version})
    db.session.commit()
    return jsonify(schema_version=1, results=results, partial=any(r.get('status') != 'acknowledged' for r in results))


@bp.post('/events/ack')
def ack_events():
    ids = (request.get_json(silent=True) or {}).get('event_ids') or []
    events = RuntimeEvent.query.filter(RuntimeEvent.event_id.in_(ids)).all() if ids else []
    for event in events:
        event.acknowledged = True
    db.session.commit()
    return jsonify(acknowledged=[event.event_id for event in events])


def _register_push_token(data):
    app = get_application(data.get('app') or request.args.get('app', 'flutter-app'))
    if not app:
        return jsonify(error='application_not_found'), 404
    if not authorized(app):
        return jsonify(error='unauthorized'), 401
    token = str(data.get('token') or data.get('push_token') or '').strip()
    if not token:
        return jsonify(error='missing_push_token'), 400
    device_id = str(data.get('device_id') or hashlib.sha256(token.encode('utf-8')).hexdigest()[:32])
    row = DeviceRegistration.query.filter_by(application_id=app.id, device_id=device_id).first() or DeviceRegistration(
        application_id=app.id,
        device_id=device_id,
        platform=str(data.get('platform') or 'unknown'),
    )
    row.push_token = token
    row.platform = str(data.get('platform') or row.platform or 'unknown')
    row.metadata_json = data.get('metadata') or row.metadata_json or {}
    row.last_seen_at = datetime.now(timezone.utc)
    db.session.add(row)
    db.session.commit()
    return jsonify(ok=True, device_id=device_id)


@bp.post('/devices/register')
def register_device():
    return _register_push_token(request.get_json(silent=True) or {})


@bp.post('/notifications/token')
def register_notification_token():
    return _register_push_token(request.get_json(silent=True) or {})
