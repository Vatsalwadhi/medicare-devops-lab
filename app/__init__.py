"""MediCare+ Hospital Management System - application factory."""
import os
from flask import Flask
from .models import db
from .security import init_security


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", os.urandom(32).hex()),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///medicare.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "false") == "true",
        PERMANENT_SESSION_LIFETIME=1800,
        APP_VERSION=os.environ.get("APP_VERSION", "dev"),
        DEPLOY_COLOR=os.environ.get("DEPLOY_COLOR", "none"),
        PHI_KEY=os.environ.get("PHI_ENCRYPTION_KEY"),
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    init_security(app)

    from .routes import main, auth, patient, doctor, admin, api
    for bp in (main.bp, auth.bp, patient.bp, doctor.bp, admin.bp, api.bp):
        app.register_blueprint(bp)

    @app.context_processor
    def inject_globals():
        return {"app_version": app.config["APP_VERSION"],
                "deploy_color": app.config["DEPLOY_COLOR"]}

    with app.app_context():
        from .seed import seed_data
        try:  # several replicas may start at once; tolerate the race
            db.create_all()
            seed_data()
        except Exception as exc:  # noqa: BLE001
            db.session.rollback()
            app.logger.warning("init/seed skipped: %s", exc.__class__.__name__)
    return app
