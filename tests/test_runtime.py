def test_runtime_bootstrap_without_release(client):
    r = client.get('/runtime/bootstrap?app=flutter-app')
    assert r.status_code == 503


def test_admin_login_page(client):
    r = client.get('/admin/login')
    assert r.status_code == 200


def test_webhook_creates_event(client):
    r = client.post('/hooks/flutter-app/config.updated', json={'version': 2})
    assert r.status_code == 200
    assert r.get_json()['ok'] is True


def test_publish_and_bootstrap(client, app):
    from app.extensions import db
    from app.models import Application, ScreenDefinition
    from app.services.runtime_service import build_release, publish_release
    with app.app_context():
        a = Application.query.filter_by(slug='flutter-app').first()
        db.session.add(ScreenDefinition(application_id=a.id, slug='home', title='Home', route='/', home=True, stac_json={'type': 'scaffold'}))
        db.session.commit()
        release = build_release(a, 'test')
        publish_release(release)
        response = client.get('/runtime/bootstrap?app=flutter-app')
        assert response.status_code == 200
        assert response.get_json()['release']['version'] == 1


def test_sync_is_idempotent(client, app):
    from app.models import Application
    with app.app_context():
        a = Application.query.filter_by(slug='flutter-app').first()
        payload = {
            'app': a.slug,
            'operations': [{
                'operation_id': 'op-1',
                'entity': 'customers',
                'entity_id': '1',
                'operation': 'update',
                'base_version': 4,
                'payload': {'name': 'x'},
            }],
        }
    assert client.post('/runtime/sync', json=payload).get_json()['results'][0]['status'] == 'acknowledged'
    assert client.post('/runtime/sync', json=payload).get_json()['results'][0]['status'] == 'acknowledged'


def test_data_api_crud_and_conflict(client, app):
    from app.extensions import db
    from app.models import Application, DataModel
    with app.app_context():
        a = Application.query.filter_by(slug='flutter-app').first()
        db.session.add(DataModel(
            application_id=a.id,
            slug='customers',
            name='Customers',
            schema_json={'fields': {'name': {'type': 'string', 'required': True}}},
        ))
        db.session.commit()
    created = client.post('/runtime/data/customers', json={'id': '1', 'data': {'name': 'Zaidan'}})
    assert created.status_code == 201
    record = created.get_json()['record']
    assert record['version'] == 1
    listed = client.get('/runtime/data/customers?page=1&per_page=10')
    assert listed.status_code == 200
    assert listed.get_json()['total'] == 1
    updated = client.patch('/runtime/data/customers/1', json={'data': {'name': 'Updated'}, 'base_version': 1})
    assert updated.status_code == 200
    conflict = client.patch('/runtime/data/customers/1', json={'data': {'name': 'Stale'}, 'base_version': 1})
    assert conflict.status_code == 409
    deleted = client.delete('/runtime/data/customers/1', headers={'If-Match': '2'})
    assert deleted.status_code == 200
    missing = client.get('/runtime/data/customers/1')
    assert missing.status_code == 404


def test_data_api_validation(client, app):
    from app.extensions import db
    from app.models import Application, DataModel
    with app.app_context():
        a = Application.query.filter_by(slug='flutter-app').first()
        db.session.add(DataModel(
            application_id=a.id,
            slug='strict',
            name='Strict',
            schema_json={'fields': {'name': {'type': 'string', 'required': True}}},
        ))
        db.session.commit()
    response = client.post('/runtime/data/strict', json={'id': '1', 'data': {}})
    assert response.status_code == 422


def test_ack_event(client):
    r = client.post('/hooks/flutter-app/config.updated', json={'version': 2})
    event_id = r.get_json()['event_id']
    assert client.post('/runtime/events/ack', json={'event_ids': [event_id]}).get_json()['acknowledged'] == [event_id]
