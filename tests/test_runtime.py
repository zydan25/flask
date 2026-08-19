def test_runtime_bootstrap_without_release(client):
    r=client.get('/runtime/bootstrap?app=flutter-app'); assert r.status_code==503

def test_admin_login_page(client):
    r=client.get('/admin/login'); assert r.status_code==200

def test_webhook_creates_event(client):
    r=client.post('/hooks/flutter-app/config.updated',json={'version':2}); assert r.status_code==200; assert r.get_json()['ok'] is True

def test_publish_and_bootstrap(client,app):
    from app.extensions import db
    from app.models import Application,ScreenDefinition
    from app.services.runtime_service import build_release,publish_release
    with app.app_context():
        a=Application.query.filter_by(slug='flutter-app').first(); db.session.add(ScreenDefinition(application_id=a.id,slug='home',title='Home',route='/',home=True,stac_json={'type':'scaffold'})); db.session.commit(); rel=build_release(a,'test'); publish_release(rel)
        rr=client.get('/runtime/bootstrap?app=flutter-app'); assert rr.status_code==200; assert rr.get_json()['release']['version']==1

def test_sync_is_idempotent(client,app):
    from app.models import Application
    with app.app_context():
        a=Application.query.filter_by(slug='flutter-app').first(); payload={'app':a.slug,'operations':[{'operation_id':'op-1','entity':'customers','entity_id':'1','operation':'update','base_version':4,'payload':{'name':'x'}}]}
    assert client.post('/runtime/sync',json=payload).get_json()['results'][0]['status']=='acknowledged'
    assert client.post('/runtime/sync',json=payload).get_json()['results'][0]['status']=='acknowledged'

def test_ack_event(client):
    r=client.post('/hooks/flutter-app/config.updated',json={'version':2}); event_id=r.get_json()['event_id']; assert client.post('/runtime/events/ack',json={'event_ids':[event_id]}).get_json()['acknowledged']==[event_id]
