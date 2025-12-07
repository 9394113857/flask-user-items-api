from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token, get_jwt
from datetime import datetime
from ..extensions import db, token_blocklist
from ..models import User
from ..utils.token_utils import generate_token  # optional helper if you prefer

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/", methods=["GET"])
def root():
    """Health check / root API route"""
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")

    return jsonify({
        "status": "running",
        "message": "Flask User Items API is healthy!",
        "current_date": current_date,
        "current_time": current_time
    }), 200


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"message": "Email already exists"}), 400

    hashed_pw = generate_password_hash(password)

    new_user = User(email=email, password=hashed_pw)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400

    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password, password):
        return jsonify({"message": "Invalid credentials"}), 401

    # store identity as string to satisfy JWT subject requirement
    access_token = create_access_token(identity=str(user.id))

    return jsonify({
        "message": "Login successful",
        "access_token": access_token
    }), 200


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    # Revoke the current JWT by storing its jti in the blocklist
    jti = get_jwt().get("jti")
    token_blocklist.add(jti)
    return jsonify({"message": "Logout successful"}), 200


@auth_bp.route("/profile", methods=["GET"])
@jwt_required()
def profile():
    # get_jwt_identity() returns string identity (we stored str(id))
    user_id_str = get_jwt_identity()
    try:
        user_id = int(user_id_str)
    except (TypeError, ValueError):
        return jsonify({"message": "Invalid token identity"}), 401

    user = User.query.get_or_404(user_id)

    return jsonify({
        "id": user.id,
        "email": user.email,
        "created_at": str(user.created_at)
    })


@auth_bp.route("/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    """
    Update the current user's profile.
    Accepts JSON: { "email": "<new>", "password": "<newpass>" }
    If password provided, it will be hashed.
    """
    user_id_str = get_jwt_identity()
    try:
        user_id = int(user_id_str)
    except (TypeError, ValueError):
        return jsonify({"message": "Invalid token identity"}), 401

    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}

    new_email = data.get("email")
    new_password = data.get("password")

    if new_email:
        # ensure no other user has this email
        existing = User.query.filter(User.email == new_email, User.id != user.id).first()
        if existing:
            return jsonify({"message": "Email already used by another user"}), 400
        user.email = new_email

    if new_password:
        user.password = generate_password_hash(new_password)

    db.session.commit()

    return jsonify({"message": "Profile updated", "id": user.id, "email": user.email}), 200
