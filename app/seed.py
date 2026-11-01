import os
import secrets
from .models import Doctor, User, db

DOCTORS = [
    ("Dr. Ananya Rao", "ananya.rao@medicare.local", "Cardiologist", "Cardiology", "MBBS, MD, DM (Cardiology)", 14, 900,
     "Interventional cardiologist focused on preventive heart care and angioplasty."),
    ("Dr. Vikram Iyer", "vikram.iyer@medicare.local", "Neurologist", "Neurology", "MBBS, MD, DM (Neurology)", 11, 850,
     "Treats migraine, epilepsy, stroke and movement disorders."),
    ("Dr. Priya Menon", "priya.menon@medicare.local", "Pediatrician", "Pediatrics", "MBBS, MD (Pediatrics)", 9, 600,
     "Child health, vaccinations and developmental care from newborns to teens."),
    ("Dr. Arjun Shah", "arjun.shah@medicare.local", "Orthopedic Surgeon", "Orthopedics", "MBBS, MS (Ortho)", 16, 800,
     "Joint replacement, sports injuries and spine care."),
    ("Dr. Kavya Nair", "kavya.nair@medicare.local", "Dermatologist", "Dermatology", "MBBS, MD (Dermatology)", 7, 650,
     "Medical and cosmetic dermatology, allergy and skin infections."),
    ("Dr. Rahul Verma", "rahul.verma@medicare.local", "General Physician", "General Medicine", "MBBS, MD (Medicine)", 12, 500,
     "Primary care, diabetes, hypertension and fever management."),
]


def seed_data():
    if User.query.filter_by(role="admin").first():
        return
    admin = User(name="Hospital Administrator", email=os.environ.get("ADMIN_EMAIL", "admin@medicare.local"), role="admin")
    admin.set_password(os.environ.get("ADMIN_PASSWORD") or secrets.token_urlsafe(12))
    db.session.add(admin)
    doc_pw = os.environ.get("DOCTOR_PASSWORD") or secrets.token_urlsafe(12)
    for name, email, spec, dept, qual, exp, fee, bio in DOCTORS:
        u = User(name=name, email=email, role="doctor", phone="+91-90000-0000")
        u.set_password(doc_pw)
        db.session.add(u)
        db.session.flush()
        db.session.add(Doctor(user_id=u.id, specialty=spec, department=dept, qualification=qual,
                              experience_years=exp, fee=fee, bio=bio))
    db.session.commit()
