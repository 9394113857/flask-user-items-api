from flask import Flask, jsonify
import os

from app.extensions import db, migrate, jwt, cors, token_blocklist
from app.routes.auth import auth_bp
from app.routes.items import items_bp


def create_app():
    app = Flask(__name__)

    # ----------------------------------------------------
    # DATABASE CONFIG (Render + Neon PostgreSQL)
    # ----------------------------------------------------
    db_url = os.getenv("DATABASE_URL", "sqlite:///local.db")

    # Fix for Render/Neon: SQLAlchemy requires postgresql://
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://")

    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # JWT Secret Key
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "supersecretkey")

    # ----------------------------------------------------
    # Initialize extensions
    # ----------------------------------------------------
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app)

    # ----------------------------------------------------
    # Health Check Route
    # ----------------------------------------------------
    @app.route("/")
    def health():
        from datetime import datetime
        return jsonify({
            "message": "Flask User Items API is running!",
            "status": "ok",
            "current_time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        })

    # ----------------------------------------------------
    # Blueprints
    # ----------------------------------------------------
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(items_bp, url_prefix="/items")

    # ----------------------------------------------------
    # JWT BLOCKLIST + ERROR HANDLERS
    # ----------------------------------------------------
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload.get("jti")
        return jti in token_blocklist

    @jwt.revoked_token_loader
    def revoked_callback(jwt_header, jwt_payload):
        return jsonify({"msg": "Token has been revoked"}), 401

    @jwt.expired_token_loader
    def expired_token(jwt_header, jwt_payload):
        return jsonify({"msg": "Token has expired"}), 401

    @jwt.invalid_token_loader
    def invalid_token(error_message):
        return jsonify({"msg": "Invalid token"}), 422

    @jwt.unauthorized_loader
    def missing_token(error_message):
        return jsonify({"msg": "Missing Authorization Header"}), 401

    return app
