from bson.binary import Binary
from bson import ObjectId


def voice_document(filename, file_bytes, user_id, chat_id):
    return {"file_name": filename, "data": Binary(file_bytes),
            "user_id": ObjectId(user_id), "chat_id": ObjectId(chat_id)}
