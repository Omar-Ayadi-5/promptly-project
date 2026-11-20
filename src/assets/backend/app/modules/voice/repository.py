from bson import ObjectId


class VoiceRepository:
    def __init__(self, database):
        self.database = database

    def insert_audio(self, document):
        return self.database["voice_messages"].insert_one(document)

    def delete_user_audio(self, user_id):
        return self.database["voice_messages"].delete_many({"user_id": ObjectId(user_id)})
