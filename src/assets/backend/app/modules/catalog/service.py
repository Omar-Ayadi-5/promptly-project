from datetime import datetime, timezone

from .models import catalog_document


class CatalogService:
    def __init__(self, repository, provider):
        self.repository = repository
        self.provider = provider

    def list_models(self):
        return self.repository.find_models()

    def get_model(self, model_id):
        return self.repository.find_model(model_id)

    def update_models_list_in_db(self):
        models_data = self.provider.fetch_models()
        needed_data = []
        for data in models_data:
            if ":free" not in data["id"]:
                continue
            needed_data.append(catalog_document(data))
        self.repository.replace_models(needed_data)
        self.repository.record_sync(datetime.now(timezone.utc).replace(tzinfo=None))

    def refresh_models(self):
        self.update_models_list_in_db()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        self.repository.record_refresh(now)
        return now
