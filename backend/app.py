
import os
from dotenv import load_dotenv
from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from models import db


def create_app():
    app = Flask(__name__)

    base = os.path.dirname(os.path.abspath(__file__))

    # Load environment variables from backend/.env
    load_dotenv(os.path.join(base, ".env"), override=True)

    app.config.update(
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL"),
        JWT_SECRET_KEY=os.getenv("JWT_SECRET"),
        UPLOAD_DIR=os.path.join(base, "uploads"),
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,
    )

    if not app.config["SQLALCHEMY_DATABASE_URI"]:
        raise ValueError("DATABASE_URL is missing from .env")

    if not app.config["JWT_SECRET_KEY"]:
        raise ValueError("JWT_SECRET is missing from .env")

    os.makedirs(app.config["UPLOAD_DIR"], exist_ok=True)

    CORS(app)
    db.init_app(app)
    JWTManager(app)

    from auth import bp as auth_bp
    from routes import bp as api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)

    @app.get("/files/<path:p>")
    def files(p):
        return send_from_directory(app.config["UPLOAD_DIR"], p)

    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    create_app().run(debug=True, port=5000)
