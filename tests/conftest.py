import pytest
from app import create_app
from config import Config
class TestConfig(Config):
    TESTING=True
    SECRET_KEY='test'
    SQLALCHEMY_DATABASE_URI='sqlite:///:memory:'
    ADMIN_EMAIL='admin@test'
    ADMIN_PASSWORD='secret'
@pytest.fixture()
def app():
    app=create_app(TestConfig); yield app
    with app.app_context():
        from app.extensions import db
        db.drop_all()
@pytest.fixture()
def client(app): return app.test_client()
