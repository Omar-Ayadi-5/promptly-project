from dataclasses import dataclass


@dataclass(frozen=True)
class GenerationRequest:
    user_id: str
    chat_id: str
    message: str
    model: str
    parameters: dict
