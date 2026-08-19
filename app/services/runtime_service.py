from datetime import datetime, timezone

from flask import current_app

from ..extensions import db
from ..models import (
    ActionDefinition,
    ApiEndpointDefinition,
    ApiProfile,
    Application,
    DataModel,
    FeatureFlag,
    PermissionDefinition,
    ResourceDefinition,
    RuntimeRelease,
    ScreenDefinition,
    WorkflowDefinition,
    checksum_for,
)


def get_application(slug):
    return Application.query.filter_by(slug=slug, active=True).first()


def current_release(app):
    if app.active_release_id:
        return db.session.get(RuntimeRelease, app.active_release_id)
    return (
        RuntimeRelease.query.filter_by(application_id=app.id, status='published')
        .order_by(RuntimeRelease.version.desc())
        .first()
    )


def _public_api_profile(profile):
    if not profile:
        return None
    auth = profile.auth_config_json or {}
    return {
        'slug': profile.slug,
        'name': profile.name,
        'base_url': profile.base_url,
        'verify_tls': bool(profile.verify_tls),
        'timeout_seconds': int(profile.timeout_seconds or 20),
        'allowed_hosts': profile.allowed_hosts_json or [],
        'auth': {
            'type': auth.get('type', 'none'),
            'token_header': auth.get('token_header', 'Authorization'),
            'scheme': auth.get('scheme', 'Bearer'),
        },
    }


def build_manifest(app):
    screens = (
        ScreenDefinition.query.filter_by(application_id=app.id, enabled=True)
        .order_by(ScreenDefinition.order_index, ScreenDefinition.id)
        .all()
    )
    actions = ActionDefinition.query.filter_by(application_id=app.id, enabled=True).all()
    workflows = WorkflowDefinition.query.filter_by(application_id=app.id, enabled=True).all()
    flags = FeatureFlag.query.filter_by(application_id=app.id).all()
    permissions = PermissionDefinition.query.filter_by(application_id=app.id).all()
    endpoints = ApiEndpointDefinition.query.filter_by(
        application_id=app.id, enabled=True
    ).all()
    models = DataModel.query.filter_by(application_id=app.id, enabled=True).all()

    profile_ids = {endpoint.profile_id for endpoint in endpoints}
    if app.api_profile_id:
        profile_ids.add(app.api_profile_id)
    profiles = {
        profile.id: profile
        for profile in (
            ApiProfile.query.filter(ApiProfile.id.in_(profile_ids)).all()
            if profile_ids
            else []
        )
    }

    screen_payload = [
        {
            'name': screen.slug,
            'title': screen.title,
            'route': screen.route,
            'home': screen.home,
            'login_required': screen.login_required,
            'order': screen.order_index,
            'stac': screen.stac_json or {},
        }
        for screen in screens
    ]
    home_screen = next(
        (screen['name'] for screen in screen_payload if screen['home']),
        screen_payload[0]['name'] if screen_payload else '',
    )

    return {
        'schema_version': int(current_app.config['RUNTIME_SCHEMA_VERSION']),
        'app_name': app.name,
        'home_screen': home_screen,
        'theme': (app.config_json or {}).get('theme', {}),
        'app': {
            'slug': app.slug,
            'name': app.name,
            'package_name': app.package_name,
            'config': app.config_json or {},
        },
        'screens': screen_payload,
        'navigation': screen_payload,
        'actions': [
            {
                'slug': action.slug,
                'name': action.name,
                'trigger': action.trigger,
                'permission': action.permission,
                'definition': action.definition_json or {},
            }
            for action in actions
        ],
        'workflows': [
            {
                'slug': workflow.slug,
                'name': workflow.name,
                'definition': workflow.definition_json or {},
            }
            for workflow in workflows
        ],
        'feature_flags': {
            flag.key: {
                'enabled': flag.enabled,
                'rules': flag.rules_json or {},
            }
            for flag in flags
        },
        'permissions': [
            {
                'key': permission.key,
                'description': permission.description,
                'default_roles': permission.default_roles_json or [],
            }
            for permission in permissions
        ],
        'api': {
            'default_profile': _public_api_profile(profiles.get(app.api_profile_id)),
            'profiles': [
                _public_api_profile(profile) for profile in profiles.values()
            ],
            'endpoints': [
                {
                    'slug': endpoint.slug,
                    'profile': endpoint.profile.slug if endpoint.profile else None,
                    'method': endpoint.method,
                    'path': endpoint.path,
                    'request_schema': endpoint.request_schema_json or {},
                    'response_mapping': endpoint.response_mapping_json or {},
                    'error_mapping': endpoint.error_mapping_json or {},
                }
                for endpoint in endpoints
            ],
        },
        'data_models': [
            {
                'slug': model.slug,
                'name': model.name,
                'schema': model.schema_json or {},
                'sync_policy': model.sync_policy_json or {},
            }
            for model in models
        ],
    }


def build_resources(app):
    rows = ResourceDefinition.query.filter_by(
        application_id=app.id, enabled=True
    ).all()
    return {
        row.key: {
            'resource_type': row.resource_type,
            'endpoint': row.endpoint,
            'cache_policy': row.cache_policy,
            'ttl_seconds': row.ttl_seconds,
            'version': row.version,
            'checksum': checksum_for(row.payload_json or {}),
            'payload': row.payload_json or {},
            'metadata': row.metadata_json or {},
        }
        for row in rows
    }


def build_release(app, notes=''):
    manifest = build_manifest(app)
    resources = build_resources(app)
    latest = (
        RuntimeRelease.query.filter_by(application_id=app.id)
        .order_by(RuntimeRelease.version.desc())
        .first()
    )
    version = 1 if latest is None else latest.version + 1
    release = RuntimeRelease(
        application_id=app.id,
        version=version,
        schema_version=int(current_app.config['RUNTIME_SCHEMA_VERSION']),
        checksum=checksum_for({'manifest': manifest, 'resources': resources}),
        status='draft',
        manifest_json=manifest,
        resources_json=resources,
        notes=notes,
    )
    db.session.add(release)
    db.session.flush()
    return release


def publish_release(release):
    app = db.session.get(Application, release.application_id)
    RuntimeRelease.query.filter_by(
        application_id=app.id, status='published'
    ).update({'status': 'archived'})
    release.status = 'published'
    release.published_at = datetime.now(timezone.utc)
    app.active_release_id = release.id
    db.session.commit()
    return release
