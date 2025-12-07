from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..extensions import db
from ..models import Item

items_bp = Blueprint("items", __name__)

@items_bp.route("/", methods=["GET"])
@jwt_required()
def get_items():
    user_id_str = get_jwt_identity()
    try:
        user_id = int(user_id_str)
    except (TypeError, ValueError):
        return jsonify({"message": "Invalid token identity"}), 401

    items = Item.query.filter_by(user_id=user_id).all()

    return jsonify([
        {"id": i.id, "name": i.name, "description": i.description}
        for i in items
    ]), 200


@items_bp.route("/", methods=["POST"])
@jwt_required()
def add_item():
    user_id_str = get_jwt_identity()
    try:
        user_id = int(user_id_str)
    except (TypeError, ValueError):
        return jsonify({"message": "Invalid token identity"}), 401

    data = request.get_json() or {}
    name = data.get("name")
    if not name:
        return jsonify({"message": "Name is required"}), 400

    new_item = Item(
        name=name,
        description=data.get("description", ""),
        user_id=user_id
    )
    db.session.add(new_item)
    db.session.commit()

    return jsonify({"message": "Item created", "id": new_item.id}), 201


@items_bp.route("/<int:item_id>", methods=["GET"])
@jwt_required()
def get_item(item_id):
    user_id_str = get_jwt_identity()
    try:
        user_id = int(user_id_str)
    except (TypeError, ValueError):
        return jsonify({"message": "Invalid token identity"}), 401

    item = Item.query.get_or_404(item_id)
    if item.user_id != user_id:
        return jsonify({"message": "Unauthorized"}), 403

    return jsonify({"id": item.id, "name": item.name, "description": item.description}), 200


@items_bp.route("/<int:item_id>", methods=["PUT"])
@jwt_required()
def update_item(item_id):
    user_id_str = get_jwt_identity()
    try:
        user_id = int(user_id_str)
    except (TypeError, ValueError):
        return jsonify({"message": "Invalid token identity"}), 401

    item = Item.query.get_or_404(item_id)

    if item.user_id != user_id:
        return jsonify({"message": "Unauthorized"}), 403

    data = request.get_json() or {}
    name = data.get("name")
    if name:
        item.name = name
    if "description" in data:
        item.description = data.get("description", "")

    db.session.commit()

    return jsonify({"message": "Item updated", "id": item.id}), 200


@items_bp.route("/<int:item_id>", methods=["DELETE"])
@jwt_required()
def delete_item(item_id):
    user_id_str = get_jwt_identity()
    try:
        user_id = int(user_id_str)
    except (TypeError, ValueError):
        return jsonify({"message": "Invalid token identity"}), 401

    item = Item.query.get_or_404(item_id)

    if item.user_id != user_id:
        return jsonify({"message": "Unauthorized"}), 403

    db.session.delete(item)
    db.session.commit()

    return jsonify({"message": "Item deleted"}), 200
