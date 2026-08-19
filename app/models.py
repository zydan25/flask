from __future__ import annotations
import hashlib
import json
import secrets
from datetime import datetime, timezone
from flask_login import UserMixin
from sqlalchemy import UniqueConstraint, Text, Index
from werkzeug.security import generate_password_hash
from .extensions import db, login_manager


def utcnow():
    return datetime.now(timezone.utc)

def stable_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))

def checksum_for(value):
    return hashlib.sha256(stable_json(value).encode('utf-8')).hexdigest()

class TimestampMixin:
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

class User(UserMixin, TimestampMixin, db.Model):
    __tablename__='users'
    id=db.Column(db.Integer, primary_key=True)
    email=db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash=db.Column(db.String(255), nullable=False)
    full_name=db.Column(db.String(255), nullable=False, default='Administrator')
    role=db.Column(db.String(50), nullable=False, default='admin')
    is_active_flag=db.Column(db.Boolean, nullable=False, default=True)
    @property
    def is_active(self): return self.is_active_flag
    def set_password(self,password): self.password_hash=generate_password_hash(password)

@login_manager.user_loader
def load_user(user_id):
    try: return db.session.get(User,int(user_id))
    except Exception: return None

class Application(TimestampMixin, db.Model):
    __tablename__='applications'
    id=db.Column(db.Integer,primary_key=True)
    slug=db.Column(db.String(120),unique=True,nullable=False,index=True)
    name=db.Column(db.String(255),nullable=False)
    package_name=db.Column(db.String(255),default='com.example.app')
    description=db.Column(Text,default='')
    active=db.Column(db.Boolean,default=True,nullable=False)
    runtime_key_hash=db.Column(db.String(255),default='',nullable=False)
    active_release_id=db.Column(db.Integer,db.ForeignKey('runtime_releases.id',use_alter=True),nullable=True)
    api_profile_id=db.Column(db.Integer,db.ForeignKey('api_profiles.id'),nullable=True)
    config_json=db.Column(db.JSON,default=dict,nullable=False)
    screens=db.relationship('ScreenDefinition',backref='application',cascade='all, delete-orphan',lazy='selectin')
    resources=db.relationship('ResourceDefinition',backref='application',cascade='all, delete-orphan',lazy='selectin')
    actions=db.relationship('ActionDefinition',backref='application',cascade='all, delete-orphan',lazy='selectin')
    workflows=db.relationship('WorkflowDefinition',backref='application',cascade='all, delete-orphan',lazy='selectin')
    flags=db.relationship('FeatureFlag',backref='application',cascade='all, delete-orphan',lazy='selectin')
    permissions=db.relationship('PermissionDefinition',backref='application',cascade='all, delete-orphan',lazy='selectin')
    data_models=db.relationship('DataModel',backref='application',cascade='all, delete-orphan',lazy='selectin')
    code_assets=db.relationship('CodeAsset',backref='application',cascade='all, delete-orphan',lazy='selectin')
    releases=db.relationship('RuntimeRelease',foreign_keys='RuntimeRelease.application_id',backref='application',cascade='all, delete-orphan',lazy='selectin')
    def rotate_runtime_key(self):
        raw=secrets.token_urlsafe(36)
        self.runtime_key_hash=generate_password_hash(raw)
        return raw

class ScreenDefinition(TimestampMixin, db.Model):
    __tablename__='screen_definitions'
    __table_args__=(UniqueConstraint('application_id','slug',name='uq_screen_app_slug'),)
    id=db.Column(db.Integer,primary_key=True); application_id=db.Column(db.Integer,db.ForeignKey('applications.id'),nullable=False,index=True)
    slug=db.Column(db.String(120),nullable=False); title=db.Column(db.String(255),nullable=False,default='Screen'); route=db.Column(db.String(255),nullable=False,default='/')
    enabled=db.Column(db.Boolean,default=True,nullable=False); login_required=db.Column(db.Boolean,default=False,nullable=False); home=db.Column(db.Boolean,default=False,nullable=False); order_index=db.Column(db.Integer,default=0,nullable=False)
    stac_json=db.Column(db.JSON,default=dict,nullable=False); metadata_json=db.Column(db.JSON,default=dict,nullable=False)

class ResourceDefinition(TimestampMixin, db.Model):
    __tablename__='resource_definitions'
    __table_args__=(UniqueConstraint('application_id','key',name='uq_resource_app_key'),)
    id=db.Column(db.Integer,primary_key=True); application_id=db.Column(db.Integer,db.ForeignKey('applications.id'),nullable=False,index=True)
    key=db.Column(db.String(160),nullable=False); resource_type=db.Column(db.String(50),nullable=False,default='json'); endpoint=db.Column(db.String(500),default='')
    cache_policy=db.Column(db.String(50),default='network_first'); ttl_seconds=db.Column(db.Integer,default=300); version=db.Column(db.Integer,default=1,nullable=False)
    payload_json=db.Column(db.JSON,default=dict,nullable=False); metadata_json=db.Column(db.JSON,default=dict,nullable=False); enabled=db.Column(db.Boolean,default=True,nullable=False)

class ApiProfile(TimestampMixin, db.Model):
    __tablename__='api_profiles'
    __table_args__=(UniqueConstraint('slug',name='uq_api_profile_slug'),)
    id=db.Column(db.Integer,primary_key=True); slug=db.Column(db.String(120),nullable=False); name=db.Column(db.String(255),nullable=False); base_url=db.Column(db.String(500),nullable=False)
    verify_tls=db.Column(db.Boolean,default=True,nullable=False); timeout_seconds=db.Column(db.Integer,default=20,nullable=False); allowed_hosts_json=db.Column(db.JSON,default=list,nullable=False)
    default_headers_json=db.Column(db.JSON,default=dict,nullable=False); auth_config_json=db.Column(db.JSON,default=dict,nullable=False); enabled=db.Column(db.Boolean,default=True,nullable=False)

class ApiEndpointDefinition(TimestampMixin, db.Model):
    __tablename__='api_endpoint_definitions'
    __table_args__=(UniqueConstraint('application_id','slug',name='uq_api_endpoint_app_slug'),)
    id=db.Column(db.Integer,primary_key=True); application_id=db.Column(db.Integer,db.ForeignKey('applications.id'),nullable=False,index=True); profile_id=db.Column(db.Integer,db.ForeignKey('api_profiles.id'),nullable=False)
    slug=db.Column(db.String(120),nullable=False); method=db.Column(db.String(16),default='GET',nullable=False); path=db.Column(db.String(500),nullable=False)
    request_schema_json=db.Column(db.JSON,default=dict,nullable=False); response_mapping_json=db.Column(db.JSON,default=dict,nullable=False); error_mapping_json=db.Column(db.JSON,default=dict,nullable=False); enabled=db.Column(db.Boolean,default=True,nullable=False)
    profile=db.relationship('ApiProfile',lazy='joined')

class ActionDefinition(TimestampMixin, db.Model):
    __tablename__='action_definitions'; __table_args__=(UniqueConstraint('application_id','slug',name='uq_action_app_slug'),)
    id=db.Column(db.Integer,primary_key=True); application_id=db.Column(db.Integer,db.ForeignKey('applications.id'),nullable=False); slug=db.Column(db.String(120),nullable=False); name=db.Column(db.String(255),nullable=False)
    trigger=db.Column(db.String(80),default='manual',nullable=False); permission=db.Column(db.String(160),default='',nullable=False); definition_json=db.Column(db.JSON,default=dict,nullable=False); enabled=db.Column(db.Boolean,default=True,nullable=False)

class WorkflowDefinition(TimestampMixin, db.Model):
    __tablename__='workflow_definitions'; __table_args__=(UniqueConstraint('application_id','slug',name='uq_workflow_app_slug'),)
    id=db.Column(db.Integer,primary_key=True); application_id=db.Column(db.Integer,db.ForeignKey('applications.id'),nullable=False); slug=db.Column(db.String(120),nullable=False); name=db.Column(db.String(255),nullable=False); definition_json=db.Column(db.JSON,default=dict,nullable=False); enabled=db.Column(db.Boolean,default=True,nullable=False)

class FeatureFlag(TimestampMixin, db.Model):
    __tablename__='feature_flags'; __table_args__=(UniqueConstraint('application_id','key',name='uq_flag_app_key'),)
    id=db.Column(db.Integer,primary_key=True); application_id=db.Column(db.Integer,db.ForeignKey('applications.id'),nullable=False); key=db.Column(db.String(160),nullable=False); enabled=db.Column(db.Boolean,default=False,nullable=False); rules_json=db.Column(db.JSON,default=dict,nullable=False)

class PermissionDefinition(TimestampMixin, db.Model):
    __tablename__='permission_definitions'; __table_args__=(UniqueConstraint('application_id','key',name='uq_permission_app_key'),)
    id=db.Column(db.Integer,primary_key=True); application_id=db.Column(db.Integer,db.ForeignKey('applications.id'),nullable=False); key=db.Column(db.String(160),nullable=False); description=db.Column(db.String(255),default=''); default_roles_json=db.Column(db.JSON,default=list,nullable=False)

class DataModel(TimestampMixin, db.Model):
    __tablename__='data_models'; __table_args__=(UniqueConstraint('application_id','slug',name='uq_data_model_app_slug'),)
    id=db.Column(db.Integer,primary_key=True); application_id=db.Column(db.Integer,db.ForeignKey('applications.id'),nullable=False); slug=db.Column(db.String(120),nullable=False); name=db.Column(db.String(255),nullable=False); schema_json=db.Column(db.JSON,default=dict,nullable=False); indexes_json=db.Column(db.JSON,default=list,nullable=False); sync_policy_json=db.Column(db.JSON,default=dict,nullable=False); enabled=db.Column(db.Boolean,default=True,nullable=False)
    records=db.relationship('DataRecord',backref='data_model',cascade='all, delete-orphan',lazy='selectin')

class DataRecord(TimestampMixin, db.Model):
    __tablename__='data_records'; __table_args__=(UniqueConstraint('model_id','record_key',name='uq_record_model_key'),Index('ix_record_model_updated','model_id','updated_at'))
    id=db.Column(db.Integer,primary_key=True); model_id=db.Column(db.Integer,db.ForeignKey('data_models.id'),nullable=False); record_key=db.Column(db.String(160),nullable=False); version=db.Column(db.Integer,default=1,nullable=False); checksum=db.Column(db.String(64),default='',nullable=False); payload_json=db.Column(db.JSON,default=dict,nullable=False); deleted=db.Column(db.Boolean,default=False,nullable=False)
    def recalc(self): self.checksum=checksum_for(self.payload_json)

class RuntimeRelease(TimestampMixin, db.Model):
    __tablename__='runtime_releases'
    id=db.Column(db.Integer,primary_key=True); application_id=db.Column(db.Integer,db.ForeignKey('applications.id'),nullable=False,index=True); version=db.Column(db.Integer,nullable=False); schema_version=db.Column(db.Integer,default=1,nullable=False); checksum=db.Column(db.String(64),nullable=False); status=db.Column(db.String(30),default='draft',nullable=False); manifest_json=db.Column(db.JSON,default=dict,nullable=False); resources_json=db.Column(db.JSON,default=dict,nullable=False); notes=db.Column(Text,default=''); published_at=db.Column(db.DateTime(timezone=True),nullable=True)
    __table_args__=(UniqueConstraint('application_id','version',name='uq_release_app_version'),)

class SyncOperation(TimestampMixin, db.Model):
    __tablename__='sync_operations'
    id=db.Column(db.Integer,primary_key=True); application_id=db.Column(db.Integer,db.ForeignKey('applications.id'),nullable=False,index=True); operation_id=db.Column(db.String(160),nullable=False,unique=True,index=True); entity=db.Column(db.String(160),nullable=False); entity_id=db.Column(db.String(160),nullable=False); operation=db.Column(db.String(30),nullable=False); base_version=db.Column(db.Integer,default=0,nullable=False); payload_json=db.Column(db.JSON,default=dict,nullable=False); status=db.Column(db.String(30),default='pending',nullable=False); error_message=db.Column(Text,default=''); server_version=db.Column(db.Integer,nullable=True); result_json=db.Column(db.JSON,default=dict,nullable=False)

class RuntimeEvent(TimestampMixin, db.Model):
    __tablename__='runtime_events'
    id=db.Column(db.Integer,primary_key=True); application_id=db.Column(db.Integer,db.ForeignKey('applications.id'),nullable=False,index=True); event_id=db.Column(db.String(160),unique=True,nullable=False,index=True); event_type=db.Column(db.String(100),nullable=False); payload_json=db.Column(db.JSON,default=dict,nullable=False); acknowledged=db.Column(db.Boolean,default=False,nullable=False); expires_at=db.Column(db.DateTime(timezone=True),nullable=True)

class DeviceRegistration(TimestampMixin, db.Model):
    __tablename__='device_registrations'
    id=db.Column(db.Integer,primary_key=True); application_id=db.Column(db.Integer,db.ForeignKey('applications.id'),nullable=False,index=True); device_id=db.Column(db.String(255),nullable=False); platform=db.Column(db.String(50),nullable=False); push_token=db.Column(Text,default=''); metadata_json=db.Column(db.JSON,default=dict,nullable=False); last_seen_at=db.Column(db.DateTime(timezone=True),default=utcnow,nullable=False)
    __table_args__=(UniqueConstraint('application_id','device_id',name='uq_device_app_id'),)

class CodeAsset(TimestampMixin, db.Model):
    __tablename__='code_assets'; __table_args__=(UniqueConstraint('application_id','slug',name='uq_code_asset_app_slug'),)
    id=db.Column(db.Integer,primary_key=True); application_id=db.Column(db.Integer,db.ForeignKey('applications.id'),nullable=False); slug=db.Column(db.String(120),nullable=False); name=db.Column(db.String(255),nullable=False); language=db.Column(db.String(50),nullable=False,default='text'); source_code=db.Column(Text,nullable=False,default=''); entrypoint=db.Column(db.String(255),default=''); execution_policy=db.Column(db.String(50),default='stored_only',nullable=False); enabled=db.Column(db.Boolean,default=True,nullable=False)

class AuditLog(TimestampMixin, db.Model):
    __tablename__='audit_logs'
    id=db.Column(db.Integer,primary_key=True); user_id=db.Column(db.Integer,db.ForeignKey('users.id'),nullable=True); action=db.Column(db.String(120),nullable=False); resource_type=db.Column(db.String(120),nullable=False); resource_id=db.Column(db.String(160),nullable=True); payload_json=db.Column(db.JSON,default=dict,nullable=False); user=db.relationship('User',lazy='joined')
