import os
from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from config import UNSAFE_SECRET_KEYS

db = SQLAlchemy()
csrf = CSRFProtect()


def create_app(config_object=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_object or "config.Config")
    app.config["APP_ENV"] = str(app.config.get("APP_ENV", "development")).strip().lower()
    if app.config["APP_ENV"] == "production":
        secret = app.config.get("SECRET_KEY")
        if not isinstance(secret, str) or not secret.strip() or secret.strip().lower() in UNSAFE_SECRET_KEYS:
            raise ValueError("Production requires a non-placeholder SECRET_KEY; set a long, random value.")
        app.config["DEMO_ACCOUNT_ENABLED"] = False
        app.config["SESSION_COOKIE_SECURE"] = True
    os.makedirs(app.instance_path, exist_ok=True)
    db.init_app(app)
    csrf.init_app(app)

    from . import models  # noqa: F401
    from .routes.auth import auth_bp
    from .routes.dashboard import dashboard_bp
    from .routes.learning import learning_bp
    from .routes.evaluation import evaluation_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(learning_bp)
    app.register_blueprint(evaluation_bp)

    @app.get("/api/csrf")
    def csrf_token_api():
        from flask_wtf.csrf import generate_csrf
        return jsonify(csrf_token=generate_csrf())

    @app.context_processor
    def inject_security_helpers():
        from flask_wtf.csrf import generate_csrf
        return {"csrf_token": generate_csrf}

    @app.errorhandler(400)
    def bad_request(error):
        if request.path.startswith("/api/") or request.is_json:
            return jsonify(error="bad_request", message=str(error)), 400
        return error

    @app.errorhandler(403)
    def forbidden(error):
        if request.path.startswith("/api/"):
            return jsonify(error="forbidden", message=str(error)), 403
        return error

    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith("/api/"):
            return jsonify(error="not_found"), 404
        return error

    with app.app_context():
        db.create_all()
    return app
