from flask import Blueprint, g, redirect, render_template, request, url_for
from ..models import Doctor, User, Appointment, db

bp = Blueprint("main", __name__)

DEPARTMENTS = [
    ("Cardiology", "Heart & vascular care, ECG, echo and cardiac rehab."),
    ("Neurology", "Brain, spine and nerve disorders with modern diagnostics."),
    ("Pediatrics", "Compassionate care for infants, children and adolescents."),
    ("Orthopedics", "Bones, joints, sports injuries and physiotherapy."),
    ("Dermatology", "Skin, hair and nail treatments by specialists."),
    ("General Medicine", "Everyday health, chronic disease and check-ups."),
]


@bp.route("/")
def index():
    stats = {
        "doctors": Doctor.query.count(),
        "patients": User.query.filter_by(role="patient").count(),
        "appointments": Appointment.query.count(),
    }
    featured = Doctor.query.limit(3).all()
    return render_template("index.html", departments=DEPARTMENTS, stats=stats, featured=featured)


@bp.route("/doctors")
def doctors():
    q = (request.args.get("q") or "").strip()
    dept = request.args.get("department") or ""
    query = Doctor.query.join(User)
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(User.name.ilike(like), Doctor.specialty.ilike(like)))
    if dept:
        query = query.filter(Doctor.department == dept)
    return render_template("doctors.html", doctors=query.order_by(User.name).all(),
                           departments=[d for d, _ in DEPARTMENTS], q=q, dept=dept)


@bp.route("/dashboard")
def dashboard():
    if not g.user:
        return redirect(url_for("auth.login"))
    return redirect(url_for({"admin": "admin.dashboard", "doctor": "doctor.dashboard"}.get(g.user.role, "patient.dashboard")))


@bp.app_errorhandler(403)
def forbidden(e):
    return render_template("error.html", code=403, message="You do not have permission to view this page."), 403


@bp.app_errorhandler(404)
def not_found(e):
    return render_template("error.html", code=404, message="The page you are looking for does not exist."), 404


@bp.app_errorhandler(400)
def bad_request(e):
    return render_template("error.html", code=400, message="Bad request. Please refresh the page and try again."), 400
