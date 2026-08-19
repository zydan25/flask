from functools import wraps
import json
from flask import Blueprint,flash,redirect,render_template,request,url_for,jsonify,abort
from flask_login import current_user,login_user,logout_user,login_required
from werkzeug.security import check_password_hash
from ..extensions import db
from ..models import User,Application,ScreenDefinition,ResourceDefinition,ActionDefinition,WorkflowDefinition,ApiProfile,ApiEndpointDefinition,DataModel,DataRecord,CodeAsset,RuntimeRelease
from ..services.audit import audit
from ..services.runtime_service import build_release,publish_release
bp=Blueprint('admin',__name__)

def admin_required(view):
 @wraps(view)
 @login_required
 def wrapper(*a,**kw):
  if current_user.role not in {'admin','editor'}:abort(403)
  return view(*a,**kw)
 return wrapper

def app_ctx():
 slug=request.args.get('app') or request.form.get('app'); return Application.query.filter_by(slug=slug).first() if slug else Application.query.order_by(Application.id).first()
def j(v,d=None):
 try:return json.loads(v or '')
 except Exception:return {} if d is None else d

@bp.route('/login',methods=['GET','POST'])
def login():
 if current_user.is_authenticated:return redirect(url_for('admin.dashboard'))
 if request.method=='POST':
  user=User.query.filter_by(email=request.form.get('email','').strip().lower()).first()
  if user and user.is_active and check_password_hash(user.password_hash,request.form.get('password','')):login_user(user);return redirect(url_for('admin.dashboard'))
  flash('بيانات الدخول غير صحيحة','danger')
 return render_template('admin/login.html')

@bp.post('/logout')
@login_required
def logout_post():logout_user();return redirect(url_for('admin.login'))

@bp.get('/')
@admin_required
def dashboard():
 a=app_ctx(); stats={'applications':Application.query.count(),'screens':ScreenDefinition.query.count(),'resources':ResourceDefinition.query.count(),'actions':ActionDefinition.query.count(),'workflows':WorkflowDefinition.query.count(),'api_profiles':ApiProfile.query.count(),'data_models':DataModel.query.count(),'releases':RuntimeRelease.query.count()}; return render_template('admin/dashboard.html',app=a,stats=stats)

@bp.route('/applications',methods=['GET','POST'])
@admin_required
def applications():
 if request.method=='POST':
  a=Application(slug=request.form['slug'].strip(),name=request.form['name'].strip(),package_name=request.form.get('package_name','com.example.app'),description=request.form.get('description',''));db.session.add(a);db.session.commit();audit('create','application',a.id);db.session.commit();flash('تم إنشاء التطبيق','success');return redirect(url_for('admin.applications'))
 return render_template('admin/applications.html',apps=Application.query.order_by(Application.id.desc()).all())

@bp.route('/screens',methods=['GET','POST'])
@admin_required
def screens():
 a=app_ctx()
 if request.method=='POST':
  r=ScreenDefinition(application_id=a.id,slug=request.form['slug'].strip(),title=request.form.get('title','Screen'),route=request.form.get('route','/'),enabled=request.form.get('enabled')=='on',login_required=request.form.get('login_required')=='on',home=request.form.get('home')=='on',order_index=int(request.form.get('order_index') or 0),stac_json=j(request.form.get('stac_json')),metadata_json=j(request.form.get('metadata_json')))
  if r.home:ScreenDefinition.query.filter_by(application_id=a.id).update({'home':False})
  db.session.add(r);db.session.commit();audit('create','screen',r.id);db.session.commit();flash('تم إنشاء الشاشة','success');return redirect(url_for('admin.screens',app=a.slug))
 return render_template('admin/screens.html',app=a,rows=ScreenDefinition.query.filter_by(application_id=a.id).order_by(ScreenDefinition.order_index,ScreenDefinition.id).all())

@bp.route('/screens/<int:screen_id>',methods=['GET','POST'])
@admin_required
def edit_screen(screen_id):
 r=db.session.get(ScreenDefinition,screen_id) or abort(404)
 if request.method=='POST':
  r.slug=request.form['slug'].strip();r.title=request.form.get('title',r.title);r.route=request.form.get('route',r.route);r.enabled=request.form.get('enabled')=='on';r.login_required=request.form.get('login_required')=='on';r.home=request.form.get('home')=='on';r.order_index=int(request.form.get('order_index') or 0);r.stac_json=j(request.form.get('stac_json'));r.metadata_json=j(request.form.get('metadata_json'));db.session.commit();audit('update','screen',r.id);db.session.commit();flash('تم حفظ الشاشة','success')
 return render_template('admin/screen_edit.html',row=r,app=r.application)

@bp.route('/resources',methods=['GET','POST'])
@admin_required
def resources():
 a=app_ctx()
 if request.method=='POST':
  r=ResourceDefinition(application_id=a.id,key=request.form['key'].strip(),resource_type=request.form.get('resource_type','json'),endpoint=request.form.get('endpoint',''),cache_policy=request.form.get('cache_policy','network_first'),ttl_seconds=int(request.form.get('ttl_seconds') or 300),payload_json=j(request.form.get('payload_json')),metadata_json=j(request.form.get('metadata_json')));db.session.add(r);db.session.commit();audit('create','resource',r.id);db.session.commit();flash('تم حفظ المورد','success');return redirect(url_for('admin.resources',app=a.slug))
 return render_template('admin/resources.html',app=a,rows=ResourceDefinition.query.filter_by(application_id=a.id).all())

@bp.route('/actions',methods=['GET','POST'])
@admin_required
def actions():
 a=app_ctx()
 if request.method=='POST':
  r=ActionDefinition(application_id=a.id,slug=request.form['slug'].strip(),name=request.form.get('name',''),trigger=request.form.get('trigger','manual'),permission=request.form.get('permission',''),definition_json=j(request.form.get('definition_json')));db.session.add(r);db.session.commit();audit('create','action',r.id);db.session.commit();flash('تم حفظ Action','success');return redirect(url_for('admin.actions',app=a.slug))
 return render_template('admin/actions.html',app=a,rows=ActionDefinition.query.filter_by(application_id=a.id).all())

@bp.route('/workflows',methods=['GET','POST'])
@admin_required
def workflows():
 a=app_ctx()
 if request.method=='POST':
  r=WorkflowDefinition(application_id=a.id,slug=request.form['slug'].strip(),name=request.form.get('name',''),definition_json=j(request.form.get('definition_json'),[]));db.session.add(r);db.session.commit();audit('create','workflow',r.id);db.session.commit();flash('تم حفظ Workflow','success');return redirect(url_for('admin.workflows',app=a.slug))
 return render_template('admin/workflows.html',app=a,rows=WorkflowDefinition.query.filter_by(application_id=a.id).all())

@bp.route('/api-profiles',methods=['GET','POST'])
@admin_required
def api_profiles():
 if request.method=='POST':
  r=ApiProfile(slug=request.form['slug'].strip(),name=request.form.get('name',''),base_url=request.form['base_url'].strip(),verify_tls=request.form.get('verify_tls')=='on',timeout_seconds=int(request.form.get('timeout_seconds') or 20),allowed_hosts_json=[x.strip() for x in request.form.get('allowed_hosts','').split(',') if x.strip()],default_headers_json=j(request.form.get('default_headers')),auth_config_json=j(request.form.get('auth_config')));db.session.add(r);db.session.commit();audit('create','api_profile',r.id);db.session.commit();flash('تم حفظ API Profile','success');return redirect(url_for('admin.api_profiles'))
 return render_template('admin/api_profiles.html',rows=ApiProfile.query.all())

@bp.route('/api-endpoints',methods=['GET','POST'])
@admin_required
def api_endpoints():
 a=app_ctx(); profiles=ApiProfile.query.all()
 if request.method=='POST':
  r=ApiEndpointDefinition(application_id=a.id,profile_id=int(request.form['profile_id']),slug=request.form['slug'].strip(),method=request.form.get('method','GET'),path=request.form['path'].strip(),request_schema_json=j(request.form.get('request_schema')),response_mapping_json=j(request.form.get('response_mapping')),error_mapping_json=j(request.form.get('error_mapping')));db.session.add(r);db.session.commit();audit('create','api_endpoint',r.id);db.session.commit();flash('تم حفظ Endpoint','success');return redirect(url_for('admin.api_endpoints',app=a.slug))
 return render_template('admin/api_endpoints.html',app=a,profiles=profiles,rows=ApiEndpointDefinition.query.filter_by(application_id=a.id).all())

@bp.route('/data-models',methods=['GET','POST'])
@admin_required
def data_models():
 a=app_ctx()
 if request.method=='POST':
  r=DataModel(application_id=a.id,slug=request.form['slug'].strip(),name=request.form.get('name',''),schema_json=j(request.form.get('schema_json')),indexes_json=j(request.form.get('indexes_json'),[]),sync_policy_json=j(request.form.get('sync_policy_json')));db.session.add(r);db.session.commit();audit('create','data_model',r.id);db.session.commit();flash('تم حفظ Data Model','success');return redirect(url_for('admin.data_models',app=a.slug))
 return render_template('admin/data_models.html',app=a,rows=DataModel.query.filter_by(application_id=a.id).all())

@bp.route('/data-models/<int:model_id>/records',methods=['GET','POST'])
@admin_required
def records(model_id):
 m=db.session.get(DataModel,model_id) or abort(404)
 if request.method=='POST':
  r=DataRecord(model_id=m.id,record_key=request.form['record_key'].strip(),payload_json=j(request.form.get('payload_json')));r.recalc();db.session.add(r);db.session.commit();audit('create','data_record',r.id);db.session.commit();flash('تم حفظ السجل','success');return redirect(url_for('admin.records',model_id=m.id))
 return render_template('admin/records.html',model=m,rows=DataRecord.query.filter_by(model_id=m.id).order_by(DataRecord.id.desc()).all())

@bp.route('/code-assets',methods=['GET','POST'])
@admin_required
def code_assets():
 a=app_ctx()
 if request.method=='POST':
  r=CodeAsset(application_id=a.id,slug=request.form['slug'].strip(),name=request.form.get('name',''),language=request.form.get('language','text'),source_code=request.form.get('source_code',''),entrypoint=request.form.get('entrypoint',''),execution_policy='stored_only');db.session.add(r);db.session.commit();audit('create','code_asset',r.id);db.session.commit();flash('تم حفظ Code Asset','success');return redirect(url_for('admin.code_assets',app=a.slug))
 return render_template('admin/code_assets.html',app=a,rows=CodeAsset.query.filter_by(application_id=a.id).all())

@bp.post('/publish')
@admin_required
def publish():
 a=app_ctx() or abort(404); r=build_release(a,request.form.get('notes',''));publish_release(r);audit('publish','release',r.id,{'version':r.version,'checksum':r.checksum});db.session.commit();flash(f'تم نشر الإصدار {r.version}','success');return redirect(url_for('admin.dashboard',app=a.slug))

@bp.get('/releases')
@admin_required
def releases():
 a=app_ctx();return render_template('admin/releases.html',app=a,rows=RuntimeRelease.query.filter_by(application_id=a.id).order_by(RuntimeRelease.version.desc()).all())

@bp.get('/export')
@admin_required
def export_app():
 a=app_ctx() or abort(404);r=RuntimeRelease.query.filter_by(application_id=a.id,status='published').order_by(RuntimeRelease.version.desc()).first()
 if not r:return jsonify(error='no_published_release'),404
 return jsonify(release=r.version,checksum=r.checksum,manifest=r.manifest_json,resources=r.resources_json)
