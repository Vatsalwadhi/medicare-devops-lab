from datetime import date, datetime

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from ..models import Appointment, Doctor, Invoice, MedicalRecord, Patient, db
from ..security import audit, decrypt_phi, login_required

bp = Blueprint("patient", __name__, url_prefix="/patient")
SLOTS = ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30"]


def me():
    p = Patient.query.filter_by(user_id=g.user.id).first()
    if not p:
        abort(403)
    return p


@bp.route("/")
@login_required("patient")
def dashboard():
    p = me()
    appts = Appointment.query.filter_by(patient_id=p.id).order_by(Appointment.date.desc(), Appointment.slot).all()
    upcoming = [a for a in appts if a.status == "Scheduled" and a.date >= date.today()]
    invoices = Invoice.query.join(Appointment).filter(Appointment.patient_id == p.id).all()
    due = sum(i.amount for i in invoices if i.status == "Unpaid")
    records = MedicalRecord.query.filter_by(patient_id=p.id).count()
    return render_template("patient/dashboard.html", patient=p, appts=appts, upcoming=upcoming,
                           due=due, records=records)


@bp.route("/book", methods=["GET", "POST"])
@login_required("patient")
def book():
    p = me()
    doctors = Doctor.query.all()
    if request.method == "POST":
        try:
            doc = db.session.get(Doctor, int(request.form.get("doctor_id", 0)))
            d = datetime.strptime(request.form.get("date", ""), "%Y-%m-%d").date()
        except ValueError:
            doc, d = None, None
        slot = request.form.get("slot")
        if not doc or not d or slot not in SLOTS:
            flash("Please choose a doctor, a valid date and a time slot.", "danger")
        elif d < date.today():
            flash("Appointments cannot be booked in the past.", "danger")
        else:
            appt = Appointment(patient_id=p.id, doctor_id=doc.id, date=d, slot=slot,
                               reason=request.form.get("reason", "")[:255])
            db.session.add(appt)
            try:
                db.session.flush()
                db.session.add(Invoice(appointment_id=appt.id, amount=doc.fee))
                db.session.commit()
                audit(f"BOOK appointment #{appt.id} with doctor #{doc.id}")
                flash(f"Appointment confirmed with {doc.user.name} on {d:%d %b %Y} at {slot}.", "success")
                return redirect(url_for("patient.dashboard"))
            except IntegrityError:
                db.session.rollback()
                flash("That slot was just taken. Please pick another time.", "warning")
    return render_template("patient/book.html", doctors=doctors, slots=SLOTS,
                           selected=request.args.get("doctor", type=int), today=date.today().isoformat())


@bp.route("/appointments/<int:aid>/cancel", methods=["POST"])
@login_required("patient")
def cancel(aid):
    a = Appointment.query.filter_by(id=aid, patient_id=me().id).first_or_404()
    if a.status == "Scheduled":
        a.status = "Cancelled"
        inv = Invoice.query.filter_by(appointment_id=a.id).first()
        if inv and inv.status == "Unpaid":
            db.session.delete(inv)
        db.session.commit()
        audit(f"CANCEL appointment #{a.id}")
        flash("Appointment cancelled.", "info")
    return redirect(url_for("patient.dashboard"))


@bp.route("/records")
@login_required("patient")
def records():
    recs = MedicalRecord.query.filter_by(patient_id=me().id).order_by(MedicalRecord.created_at.desc()).all()
    audit("VIEW own medical records")
    return render_template("patient/records.html", records=recs, decrypt=decrypt_phi)


@bp.route("/billing", methods=["GET", "POST"])
@login_required("patient")
def billing():
    p = me()
    if request.method == "POST":
        inv = Invoice.query.join(Appointment).filter(Invoice.id == request.form.get("invoice_id", type=int),
                                                     Appointment.patient_id == p.id).first_or_404()
        inv.status = "Paid"
        db.session.commit()
        audit(f"PAY invoice #{inv.id}")
        flash(f"Payment of Rs. {inv.amount} recorded for invoice #{inv.id}.", "success")
        return redirect(url_for("patient.billing"))
    invoices = Invoice.query.join(Appointment).filter(Appointment.patient_id == p.id).order_by(Invoice.id.desc()).all()
    return render_template("patient/billing.html", invoices=invoices)
