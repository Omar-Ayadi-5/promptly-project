from .models import voice_document


class VoiceService:
    def __init__(self, repository, chats, transcription):
        self.repository = repository
        self.chats = chats
        self.transcription = transcription

    def save_voice(self, filename, file_bytes, user_id, chat_id, model):
        self.repository.insert_audio(voice_document(filename, file_bytes, user_id, chat_id))
        transcript = self.transcription.transcribe(file_bytes)
        if transcript.status == "error":
            return transcript
        if transcript.text != "":
            self.chats.save_message(user_id, chat_id, transcript.text, model)
        return transcript

    def delete_user_data(self, user_id):
        self.repository.delete_user_audio(user_id)
