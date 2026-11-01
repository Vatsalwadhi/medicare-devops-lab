import socket

from flask import Blueprint, current_app, jsonify
from sqlalchemy import text

from ..models import Doctor, User, db

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.route("/health")
def health():
    try:
        db.session.execute(text("SELECT 1"))
        dbs = "up"
    except Exception:  # noqa: BLE001
        dbs = "down"
    code = 200 if dbs == "up" else 503
    return jsonify(status="ok" if code == 200 else "degraded", database=dbs), code


@bp.route("/version")
def version():
    return jsonify(app="MediCare+ HMS", version=current_app.config["APP_VERSION"],
                   color=current_app.config["DEPLOY_COLOR"], pod=socket.gethostname())


@bp.route("/doctors")
def doctors():
    rows = Doctor.query.join(User).order_by(User.name).all()
    return jsonify([{"id": d.id, "name": d.user.name, "specialty": d.specialty, "department": d.department,
                     "experience_years": d.experience_years, "fee": d.fee} for d in rows])
