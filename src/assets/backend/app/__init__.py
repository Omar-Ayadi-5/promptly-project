"""Application factory and dependency wiring for the Promptly backend."""
from flask import Flask, jsonify
from flask_cors import CORS

from .config import BACKEND_ROOT, load_config
from .infrastructure.assemblyai import AssemblyAIAdapter
from .infrastructure.mongo import create_database
from .infrastructure.openrouter import create_client, OpenRouterAdapter, OpenRouterCatalogAdapter
from .infrastructure.sendgrid import SendGridAdapter
from .modules.auth.repository import VerificationRepository
from .modules.auth.service import AuthService
from .modules.catalog.repository import CatalogRepository
from .modules.catalog.service import CatalogService
from .modules.chats.repository import ChatRepository
from .modules.chats.service import ChatService
from .modules.generation.service import GenerationService
from .modules.users.repository import UserRepository
from .modules.users.service import UserService
from .modules.voice.repository import VoiceRepository
from .modules.voice.service import VoiceService


def create_app(config=None, *, database=None, ai_client=None, transcription=None,
               mailer=None, catalog_provider=None):
    app = Flask("main", root_path=str(BACKEND_ROOT))
    app.config.from_mapping(load_config())
    if config is not None:
        app.config.update(config)
    secret = app.config.get("TOKEN_SECRET")
    if not isinstance(secret, str) or len(secret.encode()) < 32 or secret.startswith("replace-with"):
        raise ValueError("Token_secret_key must be a random secret of at least 32 bytes.")
    CORS(app, resources={r"/*": {"origins": app.config["CORS_ORIGINS"]}})

    if database is None:
        database = create_database(app.config)
        database["users"].create_index("email", unique=True)
        VerificationRepository(database).ensure_indexes()
    if ai_client is None:
        ai_client = create_client(app.config)
    if transcription is None:
        transcription = AssemblyAIAdapter()
    if mailer is None:
        mailer = SendGridAdapter()
    if catalog_provider is None:
        catalog_provider = OpenRouterCatalogAdapter()

    chats = ChatService(ChatRepository(database))
    voice_service = VoiceService(VoiceRepository(database), chats, transcription)
    users = UserService(UserRepository(database), chats, voice_service)
    catalog = CatalogService(CatalogRepository(database), catalog_provider)
    app.extensions["promptly"] = {
        "auth": AuthService(users, chats, VerificationRepository(database), mailer, secret),
        "users": users,
        "chats": chats,
        "catalog": catalog,
        "generation": GenerationService(chats, catalog, OpenRouterAdapter(ai_client)),
        "voice": voice_service,
    }

    from .modules.auth.controller import blueprint as auth
    from .modules.catalog.controller import blueprint as catalog_routes
    from .modules.chats.controller import blueprint as chat_routes
    from .modules.generation.controller import blueprint as generation
    from .modules.health.controller import blueprint as health
    from .modules.users.controller import blueprint as user_routes
    from .modules.voice.controller import blueprint as voice

    for blueprint in (catalog_routes, health, chat_routes, generation, auth, user_routes, voice):
        app.register_blueprint(blueprint)

    @app.before_request
    def limit_request_size():
        from flask import request
        from werkzeug.exceptions import RequestEntityTooLarge
        if request.content_length and request.content_length > app.config["MAX_CONTENT_LENGTH"]:
            raise RequestEntityTooLarge()

    @app.errorhandler(413)
    def upload_too_large(error):
        return jsonify({"error": "Uploads must be smaller than 10 MB."}), 413

    @app.errorhandler(500)
    def server_error(error):
        return jsonify({"error": "An unexpected error occurred. Please try again later."}), 500

    return app
