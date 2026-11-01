import re
from datetime import datetime, timedelta

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

from ..models import Patient, User, db
from ..security import audit, rate_limited

bp = Blueprint("auth", __name__)
PW_RULE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        f = request.form
        name, email, pw = f.get("name", "").strip(), f.get("email", "").strip().lower(), f.get("password", "")
        if not name or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            flash("Please enter a valid name and email address.", "danger")
        elif not PW_RULE.match(pw):
            flash("Password must be 8+ characters with upper, lower, digit and symbol.", "danger")
        elif pw != f.get("confirm"):
            flash("Passwords do not match.", "danger")
        elif User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "danger")
        else:
            u = User(name=name, email=email, phone=f.get("phone", "")[:20], role="patient")
            u.set_password(pw)
            db.session.add(u)
            db.session.flush()
            dob = f.get("dob")
            db.session.add(Patient(user_id=u.id, gender=f.get("gender"), blood_group=f.get("blood_group"),
                                   dob=datetime.strptime(dob, "%Y-%m-%d").date() if dob else None,
                                   address=f.get("address", "")[:255]))
            db.session.commit()
            flash("Registration successful. Please sign in.", "success")
            return redirect(url_for("auth.login"))
    return render_template("register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        if rate_limited(f"login:{ip}", limit=10, window=60):
            flash("Too many attempts. Please wait a minute.", "danger")
            return render_template("login.html"), 429
        email = request.form.get("email", "").strip().lower()
        u = User.query.filter_by(email=email).first()
        if u and u.locked_until and u.locked_until > datetime.utcnow():
            flash("Account temporarily locked after failed attempts. Try again later.", "danger")
        elif u and u.check_password(request.form.get("password", "")):
            session.clear()
            session["uid"] = u.id
            session.permanent = True
            u.failed_logins = 0
            db.session.commit()
            g.user = u
            audit("LOGIN success")
            nxt = request.args.get("next", "")
            return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else url_for("main.dashboard"))
        else:
            if u:
                u.failed_logins = (u.failed_logins or 0) + 1
                if u.failed_logins >= 5:
                    u.locked_until = datetime.utcnow() + timedelta(minutes=15)
                db.session.commit()
            audit(f"LOGIN failed for {email[:60]}")
            flash("Invalid email or password.", "danger")
    return render_template("login.html")


@bp.route("/logout")
def logout():
    if g.user:
        audit("LOGOUT")
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("main.index"))
