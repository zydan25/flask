from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_sock import Sock

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
sock = Sock()
