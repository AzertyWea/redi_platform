from flask import Flask, render_template, session, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()

try:
    from flask_socketio import SocketIO
    socketio = SocketIO()
    HAS_SOCKETIO = True
except ImportError:
    socketio = None
    HAS_SOCKETIO = False

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config['WTF_CSRF_ENABLED'] = True
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    if HAS_SOCKETIO:
        socketio.init_app(app, cors_allowed_origins="*")
    login_manager.login_view = 'auth.login'

    from app.services.translations import _, get_language, set_language, LANGUAGES

    @app.context_processor
    def inject_translations():
        lang = get_language()
        return dict(_=_, lang=lang, LANGUAGES=LANGUAGES)

    @app.route('/set-language/<lang>', methods=['POST'])
    def set_language_route(lang):
        set_language(lang)
        return jsonify({"status": "ok"})

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('errors/500.html'), 500

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    from app.routes.auth import auth_bp
    from app.routes.student import student_bp
    from app.routes.teacher import teacher_bp
    from app.routes.admin import admin_bp
    from app.routes.employer import employer_bp
    from app.routes.ai_upload import ai_bp
    from app.routes.notifications import notifications_bp
    from app.routes.social import social_bp
    from app.routes.unidy_admin import unidy_admin_bp
    from app.routes.unidy_registrar import unidy_registrar_bp
    from app.routes.unidy_finance import unidy_finance_bp
    from app.routes.unidy_lecturer import unidy_lecturer_bp
    from app.routes.unidy_student import unidy_student_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(social_bp)
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(teacher_bp, url_prefix='/teacher')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(employer_bp, url_prefix='/employer')
    app.register_blueprint(ai_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(unidy_admin_bp)
    app.register_blueprint(unidy_registrar_bp)
    app.register_blueprint(unidy_finance_bp)
    app.register_blueprint(unidy_lecturer_bp)
    app.register_blueprint(unidy_student_bp)

    from app.services import notification_service

    return app
