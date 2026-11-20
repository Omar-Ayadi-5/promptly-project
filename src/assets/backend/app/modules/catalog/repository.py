class CatalogRepository:
    def __init__(self, database):
        self.database = database

    def find_models(self):
        return self.database["models"].find({})

    def find_model(self, model_id):
        return self.database["models"].find_one({"id": model_id})

    def replace_models(self, documents):
        self.database["models"].delete_many({})
        if documents:
            self.database["models"].insert_many(documents)

    def record_sync(self, timestamp):
        self.database["meta"].insert_one({"timestamp": timestamp})

    def record_refresh(self, timestamp):
        self.database["last_models_updates"].update_one(
            {}, {"$set": {"timestamp": timestamp}}, upsert=True
        )
