from flask import Blueprint, current_app, jsonify, request

from openrouter_chat import OpenRouterResponseError
from ...common.authentication import token_required
from ...common.context import get_service
from ...common.errors import ModelNotFoundError, RequestValidationError
from ...infrastructure.openrouter import OpenRouterRequestError
from .schemas import generation_request

blueprint = Blueprint("generation", __name__)


@blueprint.route("/api/get_ai_response", methods=["POST"])
@token_required
def get_ai_response(current_user_id):
    data = request.get_json(silent=True)
    try:
        command = generation_request(data, current_user_id)
    except RequestValidationError as error:
        return jsonify({"error": str(error)}), error.status
    try:
        ai_reply = get_service("generation").generate_reply(command)
        return jsonify({"response": ai_reply}), 200
    except ModelNotFoundError:
        return jsonify({"error": "Model not found"}), 404
    except OpenRouterRequestError as error:
        current_app.logger.warning("OpenRouter request failed: model=%s status=%s", command.model, error.upstream_status)
        response = jsonify({"error": str(error), "code": error.code})
        if error.retry_after:
            response.headers["Retry-After"] = error.retry_after
        return response, error.status
    except OpenRouterResponseError as error:
        return jsonify({"error": str(error), "code": error.code}), error.status
    except Exception:
        current_app.logger.exception("Failed to generate or save an AI response")
        return jsonify({"error": "Failed to generate AI response. Please try again.", "code": "server_error"}), 500
