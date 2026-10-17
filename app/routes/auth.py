from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, session, url_for
from config import DEMO_ACCOUNT_EMAIL
from .. import db
from ..models import User

auth_bp = Blueprint("auth", __name__)


def page(template, payload):
    try:
        return render_template(template, **payload)
    except Exception:
        return jsonify(payload)


def auth_data():
    if request.is_json:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            abort(400, description="JSON body must be an object")
        return data
    return request.form


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return page("auth/register.html", {})
    data = auth_data()
    email, name, password = (data.get(k, "") for k in ("email", "name", "password"))
    if not all(isinstance(value, str) for value in (email, name, password)):
        return jsonify(error="email, name, and password must be strings"), 400
    email, name = email.strip().lower(), name.strip()
    if not email or not name or len(password) < 8:
        return jsonify(error="email, name, and an 8-character password are required"), 400
    if email == DEMO_ACCOUNT_EMAIL:
        return jsonify(error="email is reserved for the demo account"), 409
    if User.query.filter_by(email=email).first():
        return jsonify(error="email already registered"), 409
    user = User(email=email, name=name)
    user.set_password(password)
    db.session.add(user); db.session.commit(); session["user_id"] = user.id
    return (jsonify(user_id=user.id, email=user.email), 201) if request.is_json else redirect(url_for("dashboard.home"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return page("auth/login.html", {})
    data = auth_data()
    email, password = data.get("email", ""), data.get("password", "")
    if not isinstance(email, str) or not isinstance(password, str):
        return jsonify(error="email and password must be strings"), 400
    email = email.lower().strip()
    if email == DEMO_ACCOUNT_EMAIL and (
        not current_app.config.get("DEMO_ACCOUNT_ENABLED", False)
        or current_app.config.get("APP_ENV") == "production"
    ):
        return jsonify(error="invalid credentials"), 401
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify(error="invalid credentials"), 401
    session.clear(); session["user_id"] = user.id
    return (jsonify(user_id=user.id, name=user.name), 200) if request.is_json else redirect(url_for("dashboard.home"))


@auth_bp.post("/logout")
def logout():
    if request.is_json:
        auth_data()
    session.clear()
    return jsonify(ok=True) if request.is_json else redirect(url_for("auth.login"))
