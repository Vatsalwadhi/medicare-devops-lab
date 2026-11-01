import re
import pytest
from app import create_app
from app.models import db, User


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "Admin@12345")
    monkeypatch.setenv("DOCTOR_PASSWORD", "Doctor@12345")
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path}/t.db", "SECRET_KEY": "test"})
    with app.test_client() as c:
        yield c


def csrf(c, url):
    html = c.get(url).get_data(as_text=True)
    return re.search(r'name="csrf_token" value="([0-9a-f]+)"', html).group(1)


def register_and_login(c):
    t = csrf(c, "/register")
    c.post("/register", data={"csrf_token": t, "name": "Test Patient", "email": "p@test.com", "password": "Passw0rd!",
                              "confirm": "Passw0rd!", "gender": "Female", "blood_group": "O+"})
    t = csrf(c, "/login")
    return c.post("/login", data={"csrf_token": t, "email": "p@test.com", "password": "Passw0rd!"})


def test_home_and_doctors(client):
    assert b"MediCare" in client.get("/").data
    r = client.get("/api/doctors")
    assert r.status_code == 200 and len(r.json) == 6


def test_health_and_version(client):
    assert client.get("/api/health").json["database"] == "up"
    assert "version" in client.get("/api/version").json


def test_security_headers(client):
    h = client.get("/").headers
    assert h["X-Frame-Options"] == "DENY" and "default-src 'self'" in h["Content-Security-Policy"]


def test_csrf_required(client):
    assert client.post("/login", data={"email": "x", "password": "y"}).status_code == 400


def test_weak_password_rejected(client):
    t = csrf(client, "/register")
    r = client.post("/register", data={"csrf_token": t, "name": "A", "email": "a@b.com", "password": "weak", "confirm": "weak"})
    assert b"Password must be" in r.data


def test_patient_booking_flow(client):
    assert register_and_login(client).status_code == 302
    t = csrf(client, "/patient/book")
    r = client.post("/patient/book", data={"csrf_token": t, "doctor_id": 1, "date": "2099-01-01", "slot": "10:00",
                                           "reason": "Chest pain"}, follow_redirects=True)
    assert b"Appointment confirmed" in r.data
    r = client.post("/patient/book", data={"csrf_token": t, "doctor_id": 1, "date": "2099-01-01", "slot": "10:00"},
                    follow_redirects=True)
    assert b"slot was just taken" in r.data


def test_rbac_patient_cannot_open_admin(client):
    register_and_login(client)
    assert client.get("/admin/").status_code == 403


def test_doctor_consult_encrypts_phi(client):
    register_and_login(client)
    t = csrf(client, "/patient/book")
    client.post("/patient/book", data={"csrf_token": t, "doctor_id": 1, "date": "2099-01-02", "slot": "09:00"})
    client.get("/logout")
    t = csrf(client, "/login")
    client.post("/login", data={"csrf_token": t, "email": "ananya.rao@medicare.local", "password": "Doctor@12345"})
    t = csrf(client, "/doctor/appointments/1/consult")
    r = client.post("/doctor/appointments/1/consult", data={"csrf_token": t, "diagnosis": "Stable angina",
                    "medicine": ["Aspirin"], "dosage": ["75 mg"], "frequency": ["0-0-1"], "duration": ["30 days"]},
                    follow_redirects=True)
    assert b"Consultation saved" in r.data
    from app.models import MedicalRecord
    with client.application.app_context():
        rec = MedicalRecord.query.first()
        assert "angina" not in rec.diagnosis_enc  # stored encrypted
