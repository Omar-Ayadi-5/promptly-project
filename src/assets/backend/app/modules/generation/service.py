from model_parameters import openrouter_parameters
from openrouter_chat import build_messages

from ...common.errors import ModelNotFoundError


class GenerationService:
    def __init__(self, chats, catalog, provider):
        self.chats = chats
        self.catalog = catalog
        self.provider = provider

    def generate_reply(self, command):
        model_record = self.catalog.get_model(command.model)
        if not model_record:
            raise ModelNotFoundError("Model not found")
        history = self.chats.recent_history(command.user_id, command.chat_id)
        ai_reply = self.provider.generate(
            command.model,
            openrouter_parameters(model_record, command.parameters),
            build_messages(history, command.message),
        )
        self.chats.save_message(command.user_id, command.chat_id, ai_reply, command.model, role="AI")
        return ai_reply
