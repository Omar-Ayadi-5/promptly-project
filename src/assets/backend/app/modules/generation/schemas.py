from bson import ObjectId

from ...common.errors import RequestValidationError
from .models import GenerationRequest


def generation_request(data, current_user_id):
    if not isinstance(data, dict):
        raise RequestValidationError("Request body must be a JSON object")
    user_id = data.get("userId")
    if user_id != current_user_id:
        raise RequestValidationError("Unauthorized access", 403)
    chat_id = data.get("chatId")
    message = data.get("message")
    model = data.get("model")
    parameters = data.get("parameters")
    if parameters is None:
        parameters = {}
    if not isinstance(parameters, dict):
        raise RequestValidationError("Parameters must be an object")
    if not user_id or not chat_id or not isinstance(message, str) or not message.strip() or not isinstance(model, str) or not model:
        raise RequestValidationError("Missing or invalid required fields")
    if not ObjectId.is_valid(user_id) or not ObjectId.is_valid(chat_id):
        raise RequestValidationError("Invalid userId or chatId")
    return GenerationRequest(user_id, chat_id, message, model, parameters)
