import hmac

from flask import Blueprint, current_app, jsonify, request

from ...common.authentication import token_required
from ...common.context import get_service
from .serializers import model_summaries, model_details as serialize_model_details

blueprint = Blueprint("catalog", __name__)


@blueprint.route("/update_models", methods=["GET"])
def manual_update_trigger():
    secret_key = request.headers.get("X-Admin-Key", "")
    configured = current_app.config.get("ADMIN_SECRET")
    if not configured or not secret_key or not hmac.compare_digest(secret_key.encode(), configured.encode()):
        return jsonify({"error": "Unauthorized"}), 403
    try:
        now = get_service("catalog").refresh_models()
        return jsonify({
            "message": "✅ Models list updated successfully", "updated_at": now.isoformat(),
        }), 200
    except Exception as e:
        current_app.logger.exception("Model catalog refresh failed")
        return jsonify({"error": "Failed to update models"}), 500


@blueprint.route("/api/Load_models", methods=["GET"])
@token_required
def load_models(current_user_id):
    try:
        models_data = get_service("catalog").list_models()
        models = model_summaries(models_data)
    except:
        return jsonify({"error": "erreur fetching data"})
    return jsonify(models)


@blueprint.route("/api/Load_model_details", methods=["POST"])
@token_required
def model_details(current_user_id):
    data = request.get_json()
    try:
        model_id = data.get("model_id")
        if not model_id:
            return jsonify({"error": "No model_id provided"}), 400
        model = get_service("catalog").get_model(model_id)
        if not model:
            return jsonify({"error": "Model not found"}), 404
        return jsonify(serialize_model_details(model_id, model))
    except Exception as e:
        print("Error loading model:", e)
        return jsonify({"error": "Erreur fetching data"}), 500
