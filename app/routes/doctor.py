from datetime import date

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from ..models import Appointment, Doctor, MedicalRecord, Prescription, db
from ..security import audit, decrypt_phi, encrypt_phi, login_required

bp = Blueprint("doctor", __name__, url_prefix="/doctor")


def me():
    d = Doctor.query.filter_by(user_id=g.user.id).first()
    if not d:
        abort(403)
    return d


@bp.route("/")
@login_required("doctor")
def dashboard():
    d = me()
    appts = Appointment.query.filter_by(doctor_id=d.id).order_by(Appointment.date, Appointment.slot).all()
    today = [a for a in appts if a.date == date.today() and a.status == "Scheduled"]
    upcoming = [a for a in appts if a.date >= date.today() and a.status == "Scheduled"]
    completed = [a for a in appts if a.status == "Completed"]
    return render_template("doctor/dashboard.html", doctor=d, today=today, upcoming=upcoming, completed=completed)


@bp.route("/appointments/<int:aid>/consult", methods=["GET", "POST"])
@login_required("doctor")
def consult(aid):
    d = me()
    a = Appointment.query.filter_by(id=aid, doctor_id=d.id).first_or_404()
    if request.method == "POST":
        f = request.form
        if not f.get("diagnosis", "").strip():
            flash("Diagnosis is required.", "danger")
        else:
            rec = MedicalRecord(appointment_id=a.id, patient_id=a.patient_id, doctor_id=d.id,
                                diagnosis_enc=encrypt_phi(f["diagnosis"].strip()),
                                notes_enc=encrypt_phi(f.get("notes", "").strip()),
                                blood_pressure=f.get("bp", "")[:10], pulse=f.get("pulse", type=int),
                                temperature=f.get("temp", type=float))
            for m, ds, fr, du in zip(f.getlist("medicine"), f.getlist("dosage"), f.getlist("frequency"), f.getlist("duration")):
                if m.strip():
                    rec.prescriptions.append(Prescription(medicine=m.strip()[:120], dosage=ds[:60], frequency=fr[:60], duration=du[:60]))
            a.status = "Completed"
            db.session.add(rec)
            db.session.commit()
            audit(f"CREATE medical record #{rec.id} for patient #{a.patient_id}")
            flash("Consultation saved and prescription issued.", "success")
            return redirect(url_for("doctor.dashboard"))
    history = MedicalRecord.query.filter_by(patient_id=a.patient_id).order_by(MedicalRecord.created_at.desc()).all()
    audit(f"VIEW history of patient #{a.patient_id}")
    return render_template("doctor/consult.html", appt=a, history=history, decrypt=decrypt_phi)
