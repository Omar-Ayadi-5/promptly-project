from bson import ObjectId
from flask import Blueprint, jsonify, request

from ...common.authentication import token_required
from ...common.context import get_service
from ...common.validation import valid_password

blueprint = Blueprint("users", __name__)


@blueprint.route("/api/change_password", methods=["POST"])
@token_required
def change_password(current_user_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "A JSON object is required"}), 400
    user_id = data.get("userId")
    if user_id != current_user_id:
        return jsonify({"error": "Unauthorized access"}), 403
    current_password = data.get("currentPassword")
    new_password = data.get("newPassword")
    if not isinstance(current_password, str) or not valid_password(new_password):
        return jsonify({"error": "The new password must contain 12-128 characters"}), 400
    changed = get_service("users").change_password(current_user_id, current_password, new_password)
    if not changed:
        return jsonify({"confirm": "Current password is incorrect"}), 200
    return jsonify({"confirm": "confirmed"}), 200


@blueprint.route("/api/Delete_account", methods=["DELETE"])
@token_required
def Delete_acc(current_user_id):
    user_id = request.json["user_id"]
    if user_id != current_user_id:
        return jsonify({"error": "unauthorized access"}), 403
    user_id = ObjectId(user_id)
    get_service("users").delete_account(user_id)
    return jsonify({"confirmed": "deleted"}), 200
