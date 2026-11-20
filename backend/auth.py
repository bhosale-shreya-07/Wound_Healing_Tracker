from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.post("/register")
def register():
    d = request.get_json() or {}
    if not d.get("name") or not d.get("email") or len(d.get("password", "")) < 6:
        return jsonify(error="Name, valid email and password (6+ chars) required"), 400
    if User.query.filter_by(email=d["email"]).first():
        return jsonify(error="Email already registered"), 409
    u = User(name=d["name"], email=d["email"], password_hash=generate_password_hash(d["password"]))
    db.session.add(u)
    db.session.commit()
    return jsonify(token=create_access_token(identity=str(u.id)), name=u.name), 201


@bp.post("/login")
def login():
    d = request.get_json() or {}
    u = User.query.filter_by(email=d.get("email")).first()
    if not u or not check_password_hash(u.password_hash, d.get("password", "")):
        return jsonify(error="Invalid credentials"), 401
    return jsonify(token=create_access_token(identity=str(u.id)), name=u.name)
