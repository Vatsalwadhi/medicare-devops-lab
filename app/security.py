"""Security controls: CSRF, security headers, RBAC, rate limiting, PHI encryption, audit."""
import base64
import hashlib
import secrets
import time
from collections import defaultdict
from functools import wraps

from cryptography.fernet import Fernet
from flask import abort, current_app, flash, g, redirect, request, session, url_for

from .models import AuditLog, User, db

_rate = defaultdict(list)


def init_security(app):
    @app.before_request
    def load_user_and_csrf():
        g.user = db.session.get(User, session["uid"]) if session.get("uid") else None
        if "csrf" not in session:
            session["csrf"] = secrets.token_hex(16)
        if request.method == "POST" and not request.path.startswith("/api/"):
            if request.form.get("csrf_token") != session.get("csrf"):
                abort(400, "Invalid CSRF token")

    @app.after_request
    def security_headers(resp):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        resp.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        resp.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
            "frame-ancestors 'none'; form-action 'self'; base-uri 'self'")
        resp.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        resp.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        resp.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        resp.headers["Cache-Control"] = "no-store" if g.get("user") else resp.headers.get("Cache-Control", "no-cache")
        resp.headers["X-App-Version"] = current_app.config["APP_VERSION"]
        resp.headers["X-Deploy-Color"] = current_app.config["DEPLOY_COLOR"]
        resp.headers.pop("Server", None)
        return resp

    @app.context_processor
    def csrf_ctx():
        return {"csrf_token": session.get("csrf", ""), "current_user": g.get("user")}


def login_required(*roles):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            if not g.user:
                flash("Please sign in to continue.", "warning")
                return redirect(url_for("auth.login", next=request.path))
            if roles and g.user.role not in roles:
                audit(f"FORBIDDEN access to {request.path}")
                abort(403)
            return fn(*a, **kw)
        return wrapper
    return deco


def rate_limited(key, limit=5, window=60):
    now = time.time()
    hits = [t for t in _rate[key] if now - t < window]
    hits.append(now)
    _rate[key] = hits
    return len(hits) > limit


def _fernet():
    key = current_app.config.get("PHI_KEY")
    if not key:  # derive from SECRET_KEY when no dedicated key provided
        key = base64.urlsafe_b64encode(hashlib.sha256(current_app.config["SECRET_KEY"].encode()).digest())
    return Fernet(key)


def encrypt_phi(text):
    return _fernet().encrypt((text or "").encode()).decode()


def decrypt_phi(token):
    if not token:
        return ""
    try:
        return _fernet().decrypt(token.encode()).decode()
    except Exception:
        return "[unreadable]"


def audit(action):
    uid = g.user.id if g.get("user") else None
    db.session.add(AuditLog(user_id=uid, action=action[:255], ip=request.headers.get("X-Forwarded-For", request.remote_addr)))
    db.session.commit()
