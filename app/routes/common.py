from functools import wraps
from flask import current_app, jsonify, redirect, request, session, url_for
from config import DEMO_ACCOUNT_EMAIL
from .. import db
from ..models import User


def current_user():
    uid = session.get("user_id")
    user = db.session.get(User, uid) if uid else None
    if user and user.email == DEMO_ACCOUNT_EMAIL and not current_app.config.get("DEMO_ACCOUNT_ENABLED", False):
        session.clear()
        return None
    return user


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            if request.path.startswith("/api/") or request.is_json:
                return jsonify(error="authentication_required"), 401
            return redirect(url_for("auth.login", next=request_path()))
        return view(*args, **kwargs)
    return wrapped


def request_path():
    return request.full_path


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            return jsonify(error="authentication_required"), 401
        if not user.is_admin:
            return jsonify(error="admin_required"), 403
        return view(*args, **kwargs)
    return wrapped
