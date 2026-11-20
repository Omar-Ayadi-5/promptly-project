from bson import ObjectId


def chat_document(user_id, title, created_at):
    return {"title": title, "user_id": ObjectId(user_id), "created_at": created_at}


def message_document(user_id, chat_id, content, role, timestamp, model):
    return {
        "user_id": ObjectId(user_id),
        "chat_id": ObjectId(chat_id),
        "content": content,
        "role": role,
        "timestamp": timestamp,
        "model": model,
    }
