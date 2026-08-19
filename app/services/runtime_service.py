from datetime import datetime, timezone
from flask import current_app
from ..extensions import db
from ..models import Application, RuntimeRelease, ScreenDefinition, ResourceDefinition, ActionDefinition, WorkflowDefinition, FeatureFlag, PermissionDefinition, ApiEndpointDefinition, DataModel, checksum_for

def get_application(slug): return Application.query.filter_by(slug=slug, active=True).first()
def current_release(app):
    if app.active_release_id: return db.session.get(RuntimeRelease, app.active_release_id)
    return RuntimeRelease.query.filter_by(application_id=app.id, status='published').order_by(RuntimeRelease.version.desc()).first()

def build_manifest(app):
    screens=ScreenDefinition.query.filter_by(application_id=app.id,enabled=True).order_by(ScreenDefinition.order_index,ScreenDefinition.id).all()
    actions=ActionDefinition.query.filter_by(application_id=app.id,enabled=True).all(); workflows=WorkflowDefinition.query.filter_by(application_id=app.id,enabled=True).all()
    flags=FeatureFlag.query.filter_by(application_id=app.id).all(); permissions=PermissionDefinition.query.filter_by(application_id=app.id).all(); endpoints=ApiEndpointDefinition.query.filter_by(application_id=app.id,enabled=True).all(); models=DataModel.query.filter_by(application_id=app.id,enabled=True).all()
    return {'schema_version':current_app.config['RUNTIME_SCHEMA_VERSION'],'app':{'slug':app.slug,'name':app.name,'package_name':app.package_name,'config':app.config_json or {}},'navigation':[{'name':s.slug,'title':s.title,'route':s.route,'home':s.home,'login_required':s.login_required,'order':s.order_index,'stac':s.stac_json or {}} for s in screens],'actions':[{'slug':a.slug,'name':a.name,'trigger':a.trigger,'permission':a.permission,'definition':a.definition_json or {}} for a in actions],'workflows':[{'slug':w.slug,'name':w.name,'definition':w.definition_json or {}} for w in workflows],'feature_flags':{f.key:{'enabled':f.enabled,'rules':f.rules_json or {}} for f in flags},'permissions':[{'key':p.key,'description':p.description,'default_roles':p.default_roles_json or []} for p in permissions],'api':{'endpoints':[{'slug':e.slug,'method':e.method,'path':e.path,'request_schema':e.request_schema_json or {},'response_mapping':e.response_mapping_json or {},'error_mapping':e.error_mapping_json or {}} for e in endpoints]},'data_models':[{'slug':m.slug,'name':m.name,'schema':m.schema_json or {},'sync_policy':m.sync_policy_json or {}} for m in models]}

def build_resources(app):
    rows=ResourceDefinition.query.filter_by(application_id=app.id,enabled=True).all()
    return {r.key:{'resource_type':r.resource_type,'endpoint':r.endpoint,'cache_policy':r.cache_policy,'ttl_seconds':r.ttl_seconds,'version':r.version,'checksum':checksum_for(r.payload_json or {}),'payload':r.payload_json or {},'metadata':r.metadata_json or {}} for r in rows}

def build_release(app,notes=''):
    manifest=build_manifest(app); resources=build_resources(app); latest=RuntimeRelease.query.filter_by(application_id=app.id).order_by(RuntimeRelease.version.desc()).first(); version=1 if latest is None else latest.version+1
    release=RuntimeRelease(application_id=app.id,version=version,schema_version=current_app.config['RUNTIME_SCHEMA_VERSION'],checksum=checksum_for({'manifest':manifest,'resources':resources}),status='draft',manifest_json=manifest,resources_json=resources,notes=notes); db.session.add(release); db.session.flush(); return release

def publish_release(release):
    app=db.session.get(Application,release.application_id); RuntimeRelease.query.filter_by(application_id=app.id,status='published').update({'status':'archived'}); release.status='published'; release.published_at=datetime.now(timezone.utc); app.active_release_id=release.id; db.session.commit(); return release
