from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Wound(db.Model):
    __tablename__ = "wounds"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    label = db.Column(db.String(100), nullable=False)
    body_location = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class WoundImage(db.Model):
    __tablename__ = "wound_images"
    id = db.Column(db.Integer, primary_key=True)
    wound_id = db.Column(db.Integer, db.ForeignKey("wounds.id"), nullable=False)
    captured_on = db.Column(db.Date, nullable=False)
    original_path = db.Column(db.String(255))
    normalized_path = db.Column(db.String(255))
    overlay_path = db.Column(db.String(255))
    mask_path = db.Column(db.String(255))
    scale = db.Column(db.Float)
    px_per_cm = db.Column(db.Float)
    area_px = db.Column(db.Float)
    perimeter_px = db.Column(db.Float)
    area_cm2 = db.Column(db.Float)
    perimeter_cm = db.Column(db.Float)
    low_confidence = db.Column(db.Boolean, default=False)
    manually_corrected = db.Column(db.Boolean, default=False)


class Comparison(db.Model):
    __tablename__ = "comparisons"
    id = db.Column(db.Integer, primary_key=True)
    wound_id = db.Column(db.Integer, db.ForeignKey("wounds.id"), nullable=False)
    prev_image_id = db.Column(db.Integer, db.ForeignKey("wound_images.id"))
    curr_image_id = db.Column(db.Integer, db.ForeignKey("wound_images.id"))
    pct_change = db.Column(db.Float)
    healed_px = db.Column(db.Integer)
    grown_px = db.Column(db.Integer)
    aligned = db.Column(db.Boolean)
    diff_path = db.Column(db.String(255))
