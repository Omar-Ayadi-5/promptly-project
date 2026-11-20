from bson import ObjectId


class UserRepository:
    def __init__(self, database):
        self.database = database

    def find_by_email(self, email):
        return self.database["users"].find_one({"email": email})

    def insert_user(self, document):
        return self.database["users"].insert_one(document)

    def find_by_id(self, user_id):
        return self.database["users"].find_one({"_id": ObjectId(user_id)})

    def update_password(self, user_id, password_hash):
        return self.database["users"].update_one(
            {"_id": ObjectId(user_id)}, {"$set": {"password": password_hash}}
        )

    def delete_user(self, user_id):
        return self.database["users"].delete_one({"_id": user_id})
