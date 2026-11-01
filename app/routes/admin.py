from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy import func

from ..models import Appointment, AuditLog, Doctor, Invoice, User, db
from ..security import audit, login_required
from .auth import PW_RULE

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/")
@login_required("admin")
def dashboard():
    stats = {
        "patients": User.query.filter_by(role="patient").count(),
        "doctors": Doctor.query.count(),
        "appointments": Appointment.query.count(),
        "scheduled": Appointment.query.filter_by(status="Scheduled").count(),
        "revenue": db.session.query(func.coalesce(func.sum(Invoice.amount), 0)).filter(Invoice.status == "Paid").scalar(),
        "pending": db.session.query(func.coalesce(func.sum(Invoice.amount), 0)).filter(Invoice.status == "Unpaid").scalar(),
    }
    by_dept = (db.session.query(Doctor.department, func.count(Appointment.id))
               .outerjoin(Appointment, Appointment.doctor_id == Doctor.id)
               .group_by(Doctor.department).order_by(Doctor.department).all())
    recent = Appointment.query.order_by(Appointment.created_at.desc()).limit(10).all()
    return render_template("admin/dashboard.html", stats=stats, by_dept=by_dept, recent=recent)


@bp.route("/doctors", methods=["GET", "POST"])
@login_required("admin")
def doctors():
    if request.method == "POST":
        f = request.form
        email = f.get("email", "").strip().lower()
        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
        elif not PW_RULE.match(f.get("password", "")):
            flash("Password must be 8+ characters with upper, lower, digit and symbol.", "danger")
        else:
            u = User(name=f.get("name", "").strip()[:120], email=email, role="doctor", phone=f.get("phone", "")[:20])
            u.set_password(f["password"])
            db.session.add(u)
            db.session.flush()
            db.session.add(Doctor(user_id=u.id, specialty=f.get("specialty", "")[:80], department=f.get("department", "")[:80],
                                  qualification=f.get("qualification", "")[:120], experience_years=f.get("experience", 1, type=int),
                                  fee=f.get("fee", 500, type=int), bio=f.get("bio", "")[:1000]))
            db.session.commit()
            audit(f"ADD doctor {email}")
            flash("Doctor added successfully.", "success")
            return redirect(url_for("admin.doctors"))
    return render_template("admin/doctors.html", doctors=Doctor.query.join(User).order_by(User.name).all())


@bp.route("/appointments")
@login_required("admin")
def appointments():
    status = request.args.get("status", "")
    q = Appointment.query
    if status:
        q = q.filter_by(status=status)
    return render_template("admin/appointments.html", appts=q.order_by(Appointment.date.desc()).all(), status=status)


@bp.route("/audit")
@login_required("admin")
def audit_log():
    logs = AuditLog.query.order_by(AuditLog.ts.desc()).limit(200).all()
    users = {u.id: u.email for u in User.query.all()}
    return render_template("admin/audit.html", logs=logs, users=users)
