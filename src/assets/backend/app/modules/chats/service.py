from datetime import datetime, timezone

from .models import chat_document, message_document


class ChatService:
    def __init__(self, repository):
        self.repository = repository

    def list_chats(self, user_id):
        return self.repository.find_chats(user_id)

    def load_messages(self, user_id, chat_id):
        return self.repository.find_messages(user_id, chat_id)

    def recent_history(self, user_id, chat_id):
        return list(self.repository.recent_messages(user_id, chat_id))[::-1]

    def create_chat(self, user_id, title):
        created_at = datetime.now(timezone.utc).replace(tzinfo=None)
        return self.repository.insert_chat(chat_document(user_id, title, created_at))

    def delete_chat(self, user_id, chat_id):
        self.repository.delete_chat_messages(user_id, chat_id)
        return self.repository.delete_chat(user_id, chat_id)

    def save_message(self, user_id, chat_id, content, model, role="user", timestamp=None):
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
        return self.repository.insert_message(
            message_document(user_id, chat_id, content, role, timestamp, model)
        )

    def delete_user_data(self, user_id):
        self.repository.delete_user_messages(user_id)
        self.repository.delete_user_chats(user_id)
