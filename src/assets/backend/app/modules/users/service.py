from werkzeug.security import check_password_hash, generate_password_hash

from .models import user_document


class UserService:
    def __init__(self, repository, chats, voice):
        self.repository = repository
        self.chats = chats
        self.voice = voice

    def find_by_email(self, email):
        return self.repository.find_by_email(email)

    def create_user(self, email, password_hash):
        return self.repository.insert_user(user_document(email, password_hash))

    def change_password(self, user_id, current_password, new_password):
        user_data = self.repository.find_by_id(user_id)
        if not user_data or not check_password_hash(user_data["password"], current_password):
            return False
        self.repository.update_password(user_id, generate_password_hash(new_password))
        return True

    def delete_account(self, user_id):
        self.chats.delete_user_data(user_id)
        self.voice.delete_user_data(user_id)
        self.repository.delete_user(user_id)
