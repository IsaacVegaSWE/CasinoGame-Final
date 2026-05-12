import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_socketio import SocketIO
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()
socketio = SocketIO()


def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-in-production-abc123xyz')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///poker.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['WTF_CSRF_ENABLED'] = True

    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*", async_mode='eventlet')

    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.game import game_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(game_bp)

    from app import socket_events  # noqa: F401

    @app.template_filter('number_format')
    def number_format(value):
        try:
            return "{:,}".format(int(value))
        except (ValueError, TypeError):
            return value

    with app.app_context():
        db.create_all()

    return app
