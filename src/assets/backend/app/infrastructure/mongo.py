import certifi
from pymongo import MongoClient


def create_database(config):
    mongo_uri = config.get("MONGO_URI")
    if not mongo_uri:
        raise ValueError("MONGO_URI is required. Copy .env.example to .env and configure the database connection.")
    mongo_client = MongoClient(mongo_uri, tls=True, tlsCAFile=certifi.where())
    return mongo_client["promptly"]
