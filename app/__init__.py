from flask import Flask
from werkzeug.security import generate_password_hash

from .extensions import db, login_manager, migrate, sock
from .blueprints import ws as _ws  # noqa: F401 - registers Flask-Sock routes
from .blueprints.admin import bp as admin_bp
from .blueprints.gateway import bp as gateway_bp
from .blueprints.main import bp as main_bp
from .blueprints.runtime import bp as runtime_bp
from .blueprints.webhooks import bp as webhooks_bp
from .models import Application, ScreenDefinition, User
from .services.runtime_service import build_release, publish_release
from config import Config


def create_app(config_object=Config):
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(config_object)
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'admin.login'
    sock.init_app(app)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(runtime_bp)
    app.register_blueprint(gateway_bp)
    app.register_blueprint(webhooks_bp)
    with app.app_context():
        db.create_all()
        _seed(app)
    return app


def _seed(app):
    admin = User.query.filter_by(email=app.config['ADMIN_EMAIL']).first()
    if not admin:
        admin = User(
            email=app.config['ADMIN_EMAIL'],
            full_name='Administrator',
            role='admin',
            is_active_flag=True,
            password_hash=generate_password_hash(app.config['ADMIN_PASSWORD']),
        )
        db.session.add(admin)

    runtime_app = Application.query.filter_by(
        slug=app.config['DEFAULT_APP_SLUG']
    ).first()
    if not runtime_app:
        runtime_app = Application(
            slug=app.config['DEFAULT_APP_SLUG'],
            name='Flutter Server Runtime',
            package_name='com.alattab.dynamicapp',
            config_json={
                'client_mode': 'server_driven',
                'theme': {'primary': '#4F46E5'},
            },
        )
        db.session.add(runtime_app)
        db.session.flush()

    home = ScreenDefinition.query.filter_by(
        application_id=runtime_app.id,
        slug='home',
    ).first()
    if not home:
        home = ScreenDefinition(
            application_id=runtime_app.id,
            slug='home',
            title='الرئيسية',
            route='/',
            home=True,
            order_index=0,
            stac_json={
                'type': 'scaffold',
                'appBar': {
                    'type': 'appBar',
                    'title': {'type': 'text', 'data': 'Flutter Runtime'},
                },
                'body': {
                    'type': 'center',
                    'child': {
                        'type': 'column',
                        'mainAxisAlignment': 'center',
                        'children': [
                            {
                                'type': 'text',
                                'data': 'مرحبًا من Server-Driven Runtime',
                            },
                            {
                                'type': 'sizedBox',
                                'height': 12,
                            },
                            {
                                'type': 'text',
                                'data': 'يمكن تعديل هذه الشاشة بالكامل من لوحة الإدارة.',
                            },
                        ],
                    },
                },
            },
        )
        db.session.add(home)

    db.session.commit()

    if runtime_app.active_release_id is None:
        release = build_release(runtime_app, notes='Initial bootstrap release')
        publish_release(release)
