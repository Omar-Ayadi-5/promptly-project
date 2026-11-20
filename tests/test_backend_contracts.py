"""HTTP and persistence contracts retained by the backend architecture refactor."""
from datetime import datetime, timedelta, timezone
from io import BytesIO, StringIO
import importlib
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from bson import ObjectId
from bson.binary import Binary
import jwt
from werkzeug.security import check_password_hash, generate_password_hash

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/assets/backend"))
from app import create_app

USER = "000000000000000000000001"
CHAT = "000000000000000000000002"
OTHER = "000000000000000000000003"
EMAIL = "user@example.com"
SECRET = "test-only-token-secret-for-backend-contracts"
PASSWORD_HASH = generate_password_hash("original-password")


class BackendContracts(unittest.TestCase):
    def setUp(self):
        output = patch("sys.stdout", new=StringIO())
        output.start()
        self.addCleanup(output.stop)
        self.environment = patch.dict(os.environ, {
            "openrouter_key": "test-only",
            "Token_secret_key": SECRET,
            "ADMIN_SECRET_KEY": "test-admin",
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.database = MagicMock()
        self.collections = {name: MagicMock(name=name) for name in (
            "users", "chats", "messages", "models", "verif_codes", "voice_messages", "meta", "last_models_updates", "auth_limits",
        )}
        self.database.__getitem__.side_effect = self.collections.__getitem__
        self.database["users"].find_one.return_value = None
        self.database["users"].insert_one.return_value.inserted_id = ObjectId(USER)
        self.database["chats"].insert_one.return_value.inserted_id = ObjectId(CHAT)
        self.database["chats"].delete_one.return_value.deleted_count = 1
        self.database["models"].find.return_value = []
        self.database["models"].find_one.return_value = None
        self.database["verif_codes"].find_one.return_value = None
        self.database["auth_limits"].find_one_and_update.return_value = {"count": 1}
        self.database["verif_codes"].find_one_and_delete.return_value = None
        self.ai = MagicMock()
        self.transcription = MagicMock()
        self.transcription.transcribe.return_value = SimpleNamespace(status="completed", text="Voice text")
        self.mailer = MagicMock()
        self.mailer.send_verification_email.return_value = 202
        self.catalog = MagicMock()
        self.catalog.fetch_models.return_value = []
        self.app = create_app(
            {"TESTING": True}, database=self.database, ai_client=self.ai,
            transcription=self.transcription, mailer=self.mailer, catalog_provider=self.catalog,
        )
        self.http = self.app.test_client()
        self.headers = {"Authorization": f"bearer {jwt.encode({'user_id': USER, 'exp': datetime.now(timezone.utc) + timedelta(hours=1)}, SECRET, algorithm='HS256')}"}
        self.database.reset_mock()

    def request(self, method, path, **kwargs):
        kwargs.setdefault("headers", self.headers)
        return self.http.open(path, method=method, **kwargs)

    def assert_response(self, response, status, body):
        self.assertEqual(response.status_code, status)
        self.assertEqual(response.get_json(), body)

    def existing_user(self):
        self.database["users"].find_one.return_value = {
            "_id": ObjectId(USER), "email": EMAIL, "password": PASSWORD_HASH,
        }

    def voice_request(self, **changes):
        data = {"file": (BytesIO(b"audio-bytes"), "recording.webm"),
                "userId": USER, "chatId": CHAT, "model": "test/model:free"}
        data.update(changes)
        return self.request("POST", "/api/save_voice_message", data=data, content_type="multipart/form-data")

    def test_routes_and_http_methods_are_unchanged(self):
        routes = {(rule.rule, tuple(sorted(rule.methods - {"HEAD", "OPTIONS"})))
                  for rule in self.app.url_map.iter_rules() if rule.endpoint != "static"}
        self.assertEqual(routes, {
            ("/update_models", ("GET",)),
            ("/api/server_health", ("GET",)),
            ("/api/Load_chats_name/<user_id>", ("GET",)),
            ("/api/Load_models", ("GET",)),
            ("/api/Load_model_details", ("POST",)),
            ("/api/Load_chat_messages/<user_id>/<chatId>", ("GET",)),
            ("/api/add_new_title", ("POST",)),
            ("/api/delete_chat", ("DELETE",)),
            ("/api/save_message_ai/", ("POST",)),
            ("/api/get_ai_response", ("POST",)),
            ("/api/sign_in", ("POST",)),
            ("/api/sign_up", ("POST",)),
            ("/api/change_password", ("POST",)),
            ("/api/save_voice_message", ("POST",)),
            ("/api/send_code", ("POST",)),
            ("/api/verify_code", ("POST",)),
            ("/api/Delete_account", ("DELETE",)),
        })

    def test_health_requires_no_authentication_or_database_calls(self):
        self.assert_response(self.http.get("/api/server_health"), 200, {"status": "ok"})
        self.assertEqual(self.database.mock_calls, [])

    def test_cors_keeps_existing_development_and_production_origins(self):
        for origin in ("http://localhost:5173", "http://127.0.0.1:5173",
                       "http://localhost:4173", "http://127.0.0.1:4173"):
            with self.subTest(origin=origin):
                response = self.http.get("/api/server_health", headers={"Origin": origin})
                self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), origin)
        response = self.http.get("/api/server_health", headers={"Origin": "https://unlisted.example"})
        self.assertIsNone(response.headers.get("Access-Control-Allow-Origin"))

    def test_every_protected_route_still_requires_a_token(self):
        for method, path in (
            ("GET", f"/api/Load_chats_name/{USER}"),
            ("GET", "/api/Load_models"), ("POST", "/api/Load_model_details"),
            ("GET", f"/api/Load_chat_messages/{USER}/{CHAT}"),
            ("POST", "/api/add_new_title"), ("DELETE", "/api/delete_chat"),
            ("POST", "/api/save_message_ai/"), ("POST", "/api/get_ai_response"),
            ("POST", "/api/change_password"), ("POST", "/api/save_voice_message"),
            ("DELETE", "/api/Delete_account"),
        ):
            with self.subTest(path=path):
                self.assert_response(self.http.open(path, method=method), 401, {"message": "Token is missing!"})
        self.assertEqual(self.database.mock_calls, [])

    def test_token_errors_keep_their_existing_messages(self):
        expired = jwt.encode({"user_id": USER, "exp": datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=10)}, SECRET, algorithm="HS256")
        for authorization, message in (
            ("bearer", "Token format is invalid!"),
            ("bearer ", "Token is missing!"),
            ("bearer invalid", "Token is invalid!"),
            (f"bearer {expired}", "Token has expired!"),
        ):
            with self.subTest(message=message):
                self.assert_response(self.http.get("/api/Load_models", headers={"Authorization": authorization}),
                                     401, {"message": message})

    def test_chat_list_keeps_ids_and_titles(self):
        self.database["chats"].find.return_value = [{"_id": ObjectId(CHAT), "title": "My chat"}]
        response = self.request("GET", f"/api/Load_chats_name/{USER}")
        self.assert_response(response, 200, [{"chatId": CHAT, "title": "My chat"}])
        self.database["chats"].find.assert_called_once_with({"user_id": ObjectId(USER)})

    def test_chat_history_keeps_stored_roles_and_content_mapping(self):
        self.database["messages"].find.return_value.sort.return_value = [
            {"role": "user", "content": "Question"}, {"role": "AI", "content": "Answer"},
        ]
        response = self.request("GET", f"/api/Load_chat_messages/{USER}/{CHAT}")
        self.assert_response(response, 200, [
            {"role": "user", "message": "Question"}, {"role": "AI", "message": "Answer"},
        ])
        self.database["messages"].find.assert_called_once_with({"chat_id": ObjectId(CHAT), "user_id": ObjectId(USER)})
        self.database["messages"].find.return_value.sort.assert_called_once_with("timestamp", 1)

    def test_chat_history_rejects_a_different_user_and_invalid_chat_id(self):
        self.assert_response(self.request("GET", f"/api/Load_chat_messages/{OTHER}/{CHAT}"),
                             403, {"error": "Unauthorized access"})
        self.assert_response(self.request("GET", f"/api/Load_chat_messages/{USER}/invalid"),
                             400, {"error": "Invalid user_id or chatId"})
        self.database["messages"].find.assert_not_called()

    def test_chat_creation_keeps_the_document_and_response(self):
        response = self.request("POST", "/api/add_new_title", json={"user_id": USER, "title": "New chat"})
        self.assert_response(response, 200, {"message": "Chat created successfully", "chat_id": CHAT})
        document = self.database["chats"].insert_one.call_args.args[0]
        self.assertEqual(set(document), {"user_id", "title", "created_at"})
        self.assertEqual(document["user_id"], ObjectId(USER))
        self.assertEqual(document["title"], "New chat")
        self.assertIsInstance(document["created_at"], datetime)

    def test_chat_creation_validation_is_unchanged(self):
        self.assert_response(self.request("POST", "/api/add_new_title", json={"user_id": OTHER, "title": "New"}),
                             403, {"error": "Unauthorized access"})
        self.assert_response(self.request("POST", "/api/add_new_title", json={"user_id": USER}),
                             400, {"error": "Missing title or user_id"})
        self.database["chats"].insert_one.assert_not_called()

    def test_chat_deletion_removes_messages_before_the_chat(self):
        events = []
        self.database["messages"].delete_many.side_effect = lambda query: events.append(("messages", query))
        self.database["chats"].delete_one.side_effect = lambda query: (events.append(("chats", query)) or SimpleNamespace(deleted_count=1))
        response = self.request("DELETE", "/api/delete_chat", json={"userId": USER, "chatId": CHAT})
        self.assert_response(response, 200, {"message": "Chat deleted successfully"})
        self.assertEqual(events, [
            ("messages", {"chat_id": ObjectId(CHAT), "user_id": ObjectId(USER)}),
            ("chats", {"_id": ObjectId(CHAT), "user_id": ObjectId(USER)}),
        ])

    def test_chat_deletion_keeps_not_found_and_missing_field_responses(self):
        self.database["chats"].delete_one.return_value.deleted_count = 0
        self.assert_response(self.request("DELETE", "/api/delete_chat", json={"userId": USER, "chatId": CHAT}),
                             404, {"error": "Chat not found or unauthorized"})
        self.assert_response(self.request("DELETE", "/api/delete_chat", json={"userId": USER}),
                             400, {"error": "Missing data to delete chat"})

    def test_saving_a_text_message_does_not_generate_a_reply(self):
        response = self.request("POST", "/api/save_message_ai/", json={
            "userId": USER, "chatId": CHAT, "message": "Hello", "model": "test/model:free",
        })
        self.assert_response(response, 200, {"message": "Message saved successfully"})
        document = self.database["messages"].insert_one.call_args.args[0]
        self.assertEqual(document, {
            "user_id": ObjectId(USER), "chat_id": ObjectId(CHAT), "content": "Hello",
            "role": "user", "model": "test/model:free", "timestamp": document["timestamp"],
        })
        self.assertIsInstance(document["timestamp"], datetime)
        self.ai.with_options.assert_not_called()

    def test_message_storage_errors_keep_the_existing_failure_response(self):
        self.database["messages"].insert_one.side_effect = RuntimeError("database unavailable")
        response = self.request("POST", "/api/save_message_ai/", json={
            "userId": USER, "chatId": CHAT, "message": "Hello", "model": "test/model:free",
        })
        self.assert_response(response, 500, {"error": "Failed to save message"})

    def test_sign_in_uses_generic_failures_and_expiring_tokens(self):
        payload = {"email": EMAIL, "password": "original-password"}
        self.assert_response(self.http.post("/api/sign_in", json=payload), 401, {"error": "Invalid email or password"})
        self.existing_user()
        response = self.http.post("/api/sign_in", json=payload)
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        claims = jwt.decode(body["token"], SECRET, algorithms=["HS256"])
        self.assertEqual(claims["user_id"], USER)
        self.assertEqual(claims["exp"] - claims["iat"], 3600)
        self.assert_response(self.http.post("/api/sign_in", json={**payload, "password": "incorrect"}), 401, {"error": "Invalid email or password"})
        self.assertEqual(self.http.post("/api/sign_in", json={"email": EMAIL}).status_code, 400)

    def test_sign_in_database_failure_does_not_expose_details(self):
        self.database["users"].find_one.side_effect = RuntimeError("private database detail")
        self.app.config["PROPAGATE_EXCEPTIONS"] = False
        response = self.http.post("/api/sign_in", json={"email": EMAIL, "password": "password"})
        self.assert_response(response, 500, {"error": "An unexpected error occurred. Please try again later."})

    def test_sign_up_hashes_password_then_creates_the_first_chat(self):
        events = []
        self.database["users"].insert_one.side_effect = lambda doc: (events.append("user") or SimpleNamespace(inserted_id=ObjectId(USER)))
        self.database["chats"].insert_one.side_effect = lambda doc: events.append("chat")
        self.database["verif_codes"].find_one_and_delete.return_value = {"email": EMAIL}
        response = self.http.post("/api/sign_up", json={"email": EMAIL, "password": "new-password-long", "code": "123456"})
        self.assert_response(response, 200, {"confirmed": True})
        document = self.database["users"].insert_one.call_args.args[0]
        self.assertEqual(set(document), {"email", "password"})
        self.assertEqual(document["email"], EMAIL)
        self.assertTrue(check_password_hash(document["password"], "new-password-long"))
        first_chat = self.database["chats"].insert_one.call_args.args[0]
        self.assertEqual(first_chat["user_id"], ObjectId(USER))
        self.assertEqual(first_chat["title"], "Your First Chat")
        self.assertEqual(events, ["user", "chat"])

    def test_duplicate_sign_up_does_not_write(self):
        self.existing_user()
        self.assert_response(self.http.post("/api/sign_up", json={"email": EMAIL, "password": "new-password-long", "code": "123456"}), 400, {"error": "Email already used"})
        self.database["users"].insert_one.assert_not_called()
        self.database["chats"].insert_one.assert_not_called()

    def test_password_change_keeps_current_password_validation(self):
        self.existing_user()
        payload = {"userId": USER, "userEmail": EMAIL, "currentPassword": "incorrect", "newPassword": "new-password-long"}
        self.assert_response(self.request("POST", "/api/change_password", json=payload),
                             200, {"confirm": "Current password is incorrect"})
        self.database["users"].update_one.assert_not_called()
        payload["currentPassword"] = "original-password"
        self.assert_response(self.request("POST", "/api/change_password", json=payload),
                             200, {"confirm": "confirmed"})
        query, update = self.database["users"].update_one.call_args.args
        self.assertEqual(query, {"_id": ObjectId(USER)})
        self.assertTrue(check_password_hash(update["$set"]["password"], "new-password-long"))

    def test_account_deletion_keeps_the_existing_cascade_order(self):
        events = []
        for collection, method in (("messages", "delete_many"), ("chats", "delete_many"), ("users", "delete_one")):
            getattr(self.database[collection], method).side_effect = lambda query, name=collection: events.append((name, query))
        self.assert_response(self.request("DELETE", "/api/Delete_account", json={"user_id": USER}),
                             200, {"confirmed": "deleted"})
        self.assertEqual(events, [("messages", {"user_id": ObjectId(USER)}),
                                  ("chats", {"user_id": ObjectId(USER)}), ("users", {"_id": ObjectId(USER)})])
        self.database["voice_messages"].delete_many.assert_called_once_with({"user_id": ObjectId(USER)})
        self.database["verif_codes"].delete_many.assert_not_called()

    def test_sending_verification_code_stores_it_before_sending_email(self):
        events = []
        self.database["verif_codes"].update_one.side_effect = lambda *args, **kwargs: events.append("stored")
        self.mailer.send_verification_email.side_effect = lambda *args: (events.append("sent") or 202)
        self.assert_response(self.http.post("/api/send_code", json={"email": EMAIL}), 200, {"message": "Code sent!"})
        query, update = self.database["verif_codes"].update_one.call_args.args
        self.assertEqual(query["email"], EMAIL)
        self.assertIsInstance(update["$set"]["sent_at"], datetime)
        code = self.mailer.send_verification_email.call_args.args[1]
        self.assertTrue(code.isdigit())
        self.assertEqual(len(code), 6)
        self.assertNotIn("code", update["$set"])
        self.assertEqual(update["$set"]["code_hash"], self.app.extensions["promptly"]["auth"].code_hash(EMAIL, code))
        self.assertEqual(self.database["verif_codes"].update_one.call_args.kwargs, {"upsert": True})
        self.mailer.send_verification_email.assert_called_once_with(EMAIL, code)
        self.assertEqual(events, ["stored", "sent"])

    def test_verification_email_failure_keeps_the_stored_code(self):
        self.mailer.send_verification_email.return_value = None
        self.assert_response(self.http.post("/api/send_code", json={"email": EMAIL}),
                             503, {"error": "Failed to send email"})
        self.database["verif_codes"].update_one.assert_called_once()

    def test_sending_a_code_for_an_existing_user_does_not_write_or_send(self):
        self.existing_user()
        self.assert_response(self.http.post("/api/send_code", json={"email": EMAIL}),
                             409, {"error": "Email already used"})
        self.database["verif_codes"].update_one.assert_not_called()
        self.mailer.send_verification_email.assert_not_called()

    def test_code_verification_reads_the_latest_code_without_removing_it(self):
        self.database["verif_codes"].find_one.return_value = {"code_hash": self.app.extensions["promptly"]["auth"].code_hash(EMAIL, "123456"), "expires_at": datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=10)}
        self.assert_response(self.http.post("/api/verify_code", json={"email": EMAIL, "code": "123456"}),
                             200, {"verified": True})
        self.database["verif_codes"].find_one.assert_called_with({"email": EMAIL}, sort=[("sent_at", -1)])
        self.assert_response(self.http.post("/api/verify_code", json={"email": EMAIL, "code": "wrong"}),
                             400, {"verified": False})
        self.database["verif_codes"].delete_one.assert_not_called()

    def test_catalog_list_and_legacy_details_keep_their_shapes(self):
        model = {"id": "test/model:free", "name": "Test", "top_provider": {"max_completion_tokens": 4096}}
        self.database["models"].find.return_value = [model]
        self.assert_response(self.request("GET", "/api/Load_models"), 200, [{"id": model["id"], "name": "Test"}])
        self.database["models"].find_one.return_value = model
        self.assert_response(self.request("POST", "/api/Load_model_details", json={"model_id": model["id"]}), 200, {
            "id": model["id"], "name": "Test", "description": "No description available", "context": "N/A",
            "max_completion_tokens": 4096, "default_parameters": {},
        })

    def test_catalog_failures_keep_existing_statuses_and_messages(self):
        self.database["models"].find.side_effect = RuntimeError("database unavailable")
        self.assert_response(self.request("GET", "/api/Load_models"), 200, {"error": "erreur fetching data"})
        self.assert_response(self.request("POST", "/api/Load_model_details", json={}), 400, {"error": "No model_id provided"})
        self.assert_response(self.request("POST", "/api/Load_model_details", json={"model_id": "unknown"}),
                             404, {"error": "Model not found"})
        self.database["models"].find_one.side_effect = RuntimeError("database unavailable")
        self.assert_response(self.request("POST", "/api/Load_model_details", json={"model_id": "test"}),
                             500, {"error": "Erreur fetching data"})

    def test_catalog_refresh_filters_free_models_and_keeps_write_order(self):
        self.catalog.fetch_models.return_value = [
            {"id": "test/free:free", "name": "Test (free)", "context_length": 8192,
             "top_provider": {"max_completion_tokens": 4096}, "supported_parameters": ["temperature"]},
            {"id": "test/paid", "name": "Paid"},
        ]
        events = []
        self.database["models"].delete_many.side_effect = lambda query: events.append("delete")
        self.database["models"].insert_many.side_effect = lambda docs: events.append("insert")
        self.database["meta"].insert_one.side_effect = lambda doc: events.append("sync")
        self.database["last_models_updates"].update_one.side_effect = lambda *args, **kwargs: events.append("refresh")
        response = self.http.get("/update_models", headers={"X-Admin-Key": "test-admin"})
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["message"], "✅ Models list updated successfully")
        datetime.fromisoformat(body["updated_at"])
        self.database["models"].delete_many.assert_called_once_with({})
        self.database["models"].insert_many.assert_called_once_with([{
            "id": "test/free:free", "name": "Test", "description": "", "provider": "test",
            "context": 8192, "max_completion_tokens": 4096, "supported_parameters": ["temperature"],
            "default_parameters": None,
        }])
        self.assertEqual(events, ["delete", "insert", "sync", "refresh"])

    def test_refresh_authorization_empty_catalog_and_upstream_failure(self):
        self.assert_response(self.http.get("/update_models?key=incorrect"), 403, {"error": "Unauthorized"})
        self.catalog.fetch_models.assert_not_called()
        self.assertEqual(self.http.get("/update_models", headers={"X-Admin-Key": "test-admin"}).status_code, 200)
        self.database["models"].delete_many.assert_called_once_with({})
        self.database["models"].insert_many.assert_not_called()
        self.catalog.fetch_models.side_effect = RuntimeError("upstream unavailable")
        self.assert_response(self.http.get("/update_models", headers={"X-Admin-Key": "test-admin"}),
                             500, {"error": "Failed to update models"})

    def test_voice_stores_audio_then_transcribes_and_saves_a_user_message(self):
        events = []
        self.database["voice_messages"].insert_one.side_effect = lambda doc: events.append("audio")
        self.transcription.transcribe.side_effect = lambda content: (events.append("transcribe") or SimpleNamespace(status="completed", text="Voice text"))
        self.database["messages"].insert_one.side_effect = lambda doc: events.append("message")
        self.assert_response(self.voice_request(), 200, {"transcript": "Voice text"})
        self.database["voice_messages"].insert_one.assert_called_once_with({"file_name": "recording.webm", "data": Binary(b"audio-bytes"), "user_id": ObjectId(USER), "chat_id": ObjectId(CHAT)})
        self.transcription.transcribe.assert_called_once_with(b"audio-bytes")
        message = self.database["messages"].insert_one.call_args.args[0]
        self.assertEqual(message["content"], "Voice text")
        self.assertEqual(message["role"], "user")
        self.assertEqual(message["user_id"], ObjectId(USER))
        self.assertEqual(message["chat_id"], ObjectId(CHAT))
        self.assertEqual(events, ["audio", "transcribe", "message"])
        self.ai.with_options.assert_not_called()

    def test_voice_transcription_failure_keeps_audio_without_a_message(self):
        self.transcription.transcribe.return_value = SimpleNamespace(status="error", error="Could not transcribe")
        self.assert_response(self.voice_request(), 502, {"error": "Unable to transcribe the recording. Please try again."})
        self.database["voice_messages"].insert_one.assert_called_once()
        self.database["messages"].insert_one.assert_not_called()

    def test_empty_transcription_returns_empty_text_without_a_message(self):
        self.transcription.transcribe.return_value = SimpleNamespace(status="completed", text="")
        self.assert_response(self.voice_request(), 200, {"transcript": ""})
        self.database["messages"].insert_one.assert_not_called()

    def test_voice_upload_validation_preserves_legacy_errors(self):
        self.assert_response(self.voice_request(userId=OTHER), 403, {"error": "unauthorized access"})
        self.assert_response(self.voice_request(file=(BytesIO(b""), "")), 400, {"error": "No selected file"})
        self.assert_response(self.request("POST", "/api/save_voice_message", data={"userId": USER}),
                             400, {"error": "No file part"})
        self.database["voice_messages"].insert_one.assert_not_called()


class ApplicationFactoryTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(os.environ, {"Token_secret_key": SECRET})
        environment.start()
        self.addCleanup(environment.stop)

    def test_database_connection_is_read_from_the_environment(self):
        from app.config import load_config

        database_uri = "mongodb://test.invalid:27017/promptly"
        with patch("app.config.load_dotenv"), patch.dict(os.environ, {"MONGO_URI": database_uri}):
            self.assertEqual(load_config()["MONGO_URI"], database_uri)

    def test_missing_database_uri_stops_initialization_before_connecting(self):
        from app.config import load_config
        from app.infrastructure.mongo import create_database

        with patch("app.config.load_dotenv"), patch.dict(os.environ, {}, clear=True):
            config = load_config()
        with patch("app.infrastructure.mongo.MongoClient") as client:
            with self.assertRaisesRegex(ValueError, "MONGO_URI is required"):
                create_database(config)
        client.assert_not_called()

    def test_main_still_exposes_the_wsgi_application(self):
        with patch.dict(sys.modules), patch("app.create_database"), patch("app.create_client"):
            sys.modules.pop("main", None)
            main = importlib.import_module("main")
            response = main.app.test_client().get("/api/server_health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})

    def test_injected_dependencies_do_not_create_network_clients(self):
        with patch("app.create_database") as database_factory, patch("app.create_client") as ai_factory:
            app = create_app({"TESTING": True}, database=MagicMock(), ai_client=MagicMock())
        self.assertEqual(app.test_client().get("/api/server_health").status_code, 200)
        database_factory.assert_not_called()
        ai_factory.assert_not_called()

    def test_app_instances_do_not_share_database_state(self):
        first_db, second_db = MagicMock(), MagicMock()
        first_db["models"].find.return_value = [{"id": "first", "name": "First"}]
        second_db["models"].find.return_value = [{"id": "second", "name": "Second"}]
        with patch.dict(os.environ, {"Token_secret_key": SECRET}):
            first = create_app(database=first_db, ai_client=MagicMock())
            second = create_app(database=second_db, ai_client=MagicMock())
            headers = {"Authorization": f"bearer {jwt.encode({'user_id': USER, 'exp': datetime.now(timezone.utc) + timedelta(hours=1)}, SECRET, algorithm='HS256')}"}
            self.assertEqual(first.test_client().get("/api/Load_models", headers=headers).get_json(), [{"id": "first", "name": "First"}])
            self.assertEqual(second.test_client().get("/api/Load_models", headers=headers).get_json(), [{"id": "second", "name": "Second"}])


if __name__ == "__main__":
    unittest.main()
