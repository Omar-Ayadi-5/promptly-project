from io import BytesIO
import os

import assemblyai as aai


class AssemblyAIAdapter:
    def transcribe(self, file_bytes):
        aai.settings.api_key = os.getenv("asembly_ai_key")
        config = aai.TranscriptionConfig(speech_model=aai.SpeechModel.best)
        audio_stream = BytesIO(file_bytes)
        config = aai.TranscriptionConfig(speech_model=aai.SpeechModel.universal)
        transcriber = aai.Transcriber(config=config)
        return transcriber.transcribe(audio_stream)
