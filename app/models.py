from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20))
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="patient")  # admin|doctor|patient
    failed_logins = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw, method="scrypt")

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)


class Doctor(db.Model):
    __tablename__ = "doctors"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    specialty = db.Column(db.String(80), nullable=False)
    department = db.Column(db.String(80), nullable=False)
    qualification = db.Column(db.String(120))
    experience_years = db.Column(db.Integer, default=1)
    fee = db.Column(db.Integer, default=500)
    bio = db.Column(db.Text)
    user = db.relationship("User")


class Patient(db.Model):
    __tablename__ = "patients"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    dob = db.Column(db.Date)
    gender = db.Column(db.String(10))
    blood_group = db.Column(db.String(5))
    address = db.Column(db.String(255))
    user = db.relationship("User")


class Appointment(db.Model):
    __tablename__ = "appointments"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    slot = db.Column(db.String(10), nullable=False)
    reason = db.Column(db.String(255))
    status = db.Column(db.String(20), default="Scheduled")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    patient = db.relationship("Patient")
    doctor = db.relationship("Doctor")
    __table_args__ = (db.UniqueConstraint("doctor_id", "date", "slot", name="uq_doctor_slot"),)


class MedicalRecord(db.Model):
    __tablename__ = "medical_records"
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointments.id"))
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False)
    diagnosis_enc = db.Column(db.Text, nullable=False)   # PHI encrypted at rest
    notes_enc = db.Column(db.Text)
    blood_pressure = db.Column(db.String(10))
    pulse = db.Column(db.Integer)
    temperature = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    doctor = db.relationship("Doctor")
    prescriptions = db.relationship("Prescription", backref="record", cascade="all, delete-orphan")


class Prescription(db.Model):
    __tablename__ = "prescriptions"
    id = db.Column(db.Integer, primary_key=True)
    record_id = db.Column(db.Integer, db.ForeignKey("medical_records.id"), nullable=False)
    medicine = db.Column(db.String(120), nullable=False)
    dosage = db.Column(db.String(60))
    frequency = db.Column(db.String(60))
    duration = db.Column(db.String(60))


class Invoice(db.Model):
    __tablename__ = "invoices"
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointments.id"), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(10), default="Unpaid")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    appointment = db.relationship("Appointment")


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    action = db.Column(db.String(255), nullable=False)
    ip = db.Column(db.String(45))
    ts = db.Column(db.DateTime, default=datetime.utcnow)
