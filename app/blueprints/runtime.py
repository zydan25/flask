from flask import Blueprint,jsonify,request
from werkzeug.security import check_password_hash
from ..extensions import db
from ..models import RuntimeRelease,SyncOperation,RuntimeEvent,DeviceRegistration
from ..services.runtime_service import get_application,current_release
bp=Blueprint('runtime',__name__,url_prefix='/runtime')

def authorized(app):
    if not app.runtime_key_hash:return True
    token=request.headers.get('X-Runtime-Key') or request.headers.get('Authorization','').removeprefix('Bearer ').strip()
    return bool(token and check_password_hash(app.runtime_key_hash,token))

@bp.get('/bootstrap')
def bootstrap():
    app=get_application(request.args.get('app','flutter-app'))
    if not app:return jsonify(error='application_not_found'),404
    release=current_release(app)
    if not release:return jsonify(error='no_published_release'),503
    if not authorized(app):return jsonify(error='unauthorized'),401
    return jsonify(schema_version=release.schema_version,app={'slug':app.slug,'name':app.name,'package_name':app.package_name},release={'version':release.version,'checksum':release.checksum,'published_at':release.published_at.isoformat() if release.published_at else None},manifest_url=f'/runtime/manifest?app={app.slug}&version={release.version}',resources_url=f'/runtime/resources?app={app.slug}&version={release.version}',sync_url=f'/runtime/sync?app={app.slug}',events_ack_url='/runtime/events/ack',events_ws_url=f'/runtime/events/ws?app={app.slug}',client_mode=(app.config_json or {}).get('client_mode','server_driven'))

@bp.get('/manifest')
def manifest():
    app=get_application(request.args.get('app','flutter-app'))
    if not app:return jsonify(error='application_not_found'),404
    release=current_release(app)
    if not release:return jsonify(error='no_published_release'),503
    return jsonify(schema_version=release.schema_version,version=release.version,checksum=release.checksum,**(release.manifest_json or {}))

@bp.get('/resources')
def resources():
    app=get_application(request.args.get('app','flutter-app'))
    if not app:return jsonify(error='application_not_found'),404
    release=current_release(app)
    if not release:return jsonify(error='no_published_release'),503
    keys=[k for k in request.args.get('keys','').split(',') if k]; payload=release.resources_json or {}; payload={k:payload[k] for k in keys if k in payload} if keys else payload
    return jsonify(schema_version=release.schema_version,version=release.version,resources=payload)

@bp.post('/sync')
def sync():
    data=request.get_json(silent=True) or {}; app=get_application(data.get('app') or request.args.get('app','flutter-app'))
    if not app:return jsonify(error='application_not_found'),404
    if not authorized(app):return jsonify(error='unauthorized'),401
    results=[]
    for item in data.get('operations') or []:
        op_id=str(item.get('operation_id','')).strip()
        if not op_id:results.append({'status':'rejected','error':'missing_operation_id'}); continue
        existing=SyncOperation.query.filter_by(operation_id=op_id).first()
        if existing: results.append({'operation_id':op_id,'status':existing.status,'result':existing.result_json or {},'server_version':existing.server_version}); continue
        op=SyncOperation(application_id=app.id,operation_id=op_id,entity=str(item.get('entity','')),entity_id=str(item.get('entity_id','')),operation=str(item.get('operation','update')),base_version=int(item.get('base_version') or 0),payload_json=item.get('payload') or {},status='acknowledged',server_version=int(item.get('base_version') or 0)+1)
        db.session.add(op); results.append({'operation_id':op_id,'status':'acknowledged','server_version':op.server_version})
    db.session.commit(); return jsonify(schema_version=1,results=results,partial=any(r.get('status')!='acknowledged' for r in results))

@bp.post('/events/ack')
def ack_events():
    ids=(request.get_json(silent=True) or {}).get('event_ids') or []; events=RuntimeEvent.query.filter(RuntimeEvent.event_id.in_(ids)).all() if ids else []
    for e in events:e.acknowledged=True
    db.session.commit(); return jsonify(acknowledged=[e.event_id for e in events])

@bp.post('/devices/register')
def register_device():
    data=request.get_json(silent=True) or {}; app=get_application(data.get('app','flutter-app'))
    if not app:return jsonify(error='application_not_found'),404
    device_id=str(data.get('device_id','')).strip()
    if not device_id:return jsonify(error='missing_device_id'),400
    row=DeviceRegistration.query.filter_by(application_id=app.id,device_id=device_id).first() or DeviceRegistration(application_id=app.id,device_id=device_id)
    row.platform=str(data.get('platform','unknown')); row.push_token=str(data.get('push_token','')); row.metadata_json=data.get('metadata') or {}; db.session.add(row); db.session.commit(); return jsonify(ok=True)
