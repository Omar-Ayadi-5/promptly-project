from datetime import datetime, timezone

from bson import ObjectId
from flask import Blueprint, jsonify, request

from ...common.authentication import token_required
from ...common.context import get_service
from .serializers import chat_summaries, chat_messages

blueprint = Blueprint("chats", __name__)


@blueprint.route("/api/Load_chats_name/<user_id>", methods=['GET'])
@token_required
def LoadChats(current_user_id, user_id):
    if current_user_id != user_id:
        return jsonify({"error": "Unauthorized access"}), 403
    try:
        user_object_id = ObjectId(user_id)
    except:
        return jsonify({"error": "Invalid user_id"}), 400
    user_chats = get_service("chats").list_chats(user_object_id)
    return jsonify(chat_summaries(user_chats))


@blueprint.route("/api/Load_chat_messages/<user_id>/<chatId>", methods=["GET"])
@token_required
def load_messages(current_user_id, user_id, chatId):
    if current_user_id != user_id:
        return jsonify({"error": "Unauthorized access"}), 403
    try:
        user_id = ObjectId(user_id)
        chatId = ObjectId(chatId)
    except:
        return jsonify({"error": "Invalid user_id or chatId"}), 400
    all_messages = get_service("chats").load_messages(user_id, chatId)
    messages = chat_messages(all_messages)
    return jsonify(messages)


@blueprint.route("/api/add_new_title", methods=["POST"])
@token_required
def newchat(current_user_id):
    data = request.get_json()
    user_id = data.get("user_id")
    if user_id != current_user_id:
        return jsonify({"error": "Unauthorized access"}), 403
    title = data.get("title")
    if not title or not user_id:
        return jsonify({"error": "Missing title or user_id"}), 400
    result = get_service("chats").create_chat(user_id, title)
    return jsonify({"message": "Chat created successfully", "chat_id": str(result.inserted_id)}), 200


@blueprint.route("/api/delete_chat", methods=["DELETE"])
@token_required
def delete_chat(current_user_id):
    try:
        data = request.get_json()
        user_id = data.get("userId")
        chatId = data.get("chatId")
        if user_id != current_user_id:
            return jsonify({"error": "Unauthorized access"}), 403
        if not chatId or not user_id:
            return jsonify({"error": "Missing data to delete chat"}), 400
    except:
        return jsonify({"error": "Chat not found or unauthorized"}), 404
    try:
        result = get_service("chats").delete_chat(user_id, chatId)
    except Exception as e:
        return jsonify({"error": f"Invalid ID format: {str(e)}"}), 400
    if result.deleted_count == 0:
        return jsonify({"error": "Chat not found or unauthorized"}), 404
    return jsonify({"message": "Chat deleted successfully"}), 200


@blueprint.route("/api/save_message_ai/", methods=["POST"])
@token_required
def ai_response(current_user_id):
    data = request.get_json()
    user_id = data.get("userId")
    if user_id != current_user_id:
        return jsonify({"error": "Unauthorized access"}), 403
    chat_id = data.get("chatId")
    message = data.get("message")
    model = data.get("model")
    timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
    if not all([user_id, chat_id, message, model]):
        return jsonify({"error": "Missing required fields"}), 400
    try:
        get_service("chats").save_message(user_id, chat_id, message, model, timestamp=timestamp)
        return jsonify({"message": "Message saved successfully"}), 200
    except Exception as e:
        return jsonify({"error": "Failed to save message"}), 500
