from bson import ObjectId


class ChatRepository:
    def __init__(self, database):
        self.database = database

    def find_chats(self, user_id):
        return self.database["chats"].find({"user_id": user_id})

    def find_messages(self, user_id, chat_id):
        return self.database["messages"].find({"chat_id": chat_id, "user_id": user_id}).sort("timestamp", 1)

    def recent_messages(self, user_id, chat_id):
        return self.database["messages"].find({
            "user_id": ObjectId(user_id), "chat_id": ObjectId(chat_id),
        }).sort("timestamp", -1).limit(6)

    def insert_chat(self, document):
        return self.database["chats"].insert_one(document)

    def insert_message(self, document):
        return self.database["messages"].insert_one(document)

    def delete_chat_messages(self, user_id, chat_id):
        return self.database["messages"].delete_many({
            "chat_id": ObjectId(chat_id), "user_id": ObjectId(user_id),
        })

    def delete_chat(self, user_id, chat_id):
        return self.database["chats"].delete_one({
            "_id": ObjectId(chat_id), "user_id": ObjectId(user_id),
        })

    def delete_user_messages(self, user_id):
        return self.database["messages"].delete_many({"user_id": user_id})

    def delete_user_chats(self, user_id):
        return self.database["chats"].delete_many({"user_id": user_id})
