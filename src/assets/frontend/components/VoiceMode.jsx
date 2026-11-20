import { API_BASE_URL } from '../api';
import { useEffect, useRef, useState } from "react";
import "./ChatInput.css";
import { useAuth } from "../authContext";
import { filterParameters } from '../modelParameters';
import { readAIResponse } from '../aiResponse';

function VoiceMode({ onCancel, onNewMessages, setIsLoading, userId, chatId, selectedModel, generationParams, modelDetails, }) {
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [isSending, setIsSending] = useState(false);
  const streamRef = useRef(null);
  const recorderRef = useRef(null);

  useEffect(() => () => {
    if (recorderRef.current) recorderRef.current.onstop = null;
    if (recorderRef.current?.state === 'recording') recorderRef.current.stop();
    streamRef.current?.getTracks().forEach(track => track.stop());
  }, []);

  useEffect(() => () => {
    if (audioUrl) URL.revokeObjectURL(audioUrl);
  }, [audioUrl]);


  const { token } = useAuth();

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const recorder = new MediaRecorder(stream);
      recorderRef.current = recorder;
      const chunks = [];

      recorder.ondataavailable = (e) => chunks.push(e.data);

      recorder.onstop = () => {
        const blob = new Blob(chunks, { type: recorder.mimeType || "audio/webm" });
        const url = URL.createObjectURL(blob);
        setAudioBlob(blob);
        setAudioUrl(url);
        stream.getTracks().forEach(track => track.stop());
      };

      recorder.start();
      setMediaRecorder(recorder);
      setAudioBlob(null); // reset previous audio
      setAudioUrl(null);
      setIsRecording(true);
    } catch {
      streamRef.current?.getTracks().forEach(track => track.stop());
      alert("Microphone permission denied.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorder) {
      mediaRecorder.stop();
      setIsRecording(false);
    }
  };

  const sendVoice = async () => {
    if (!audioBlob) return;
    if (selectedModel == "no_model") {
      window.alert("click on Model and select a model");
      return;
    }
    setAudioUrl(null);
    const formData = new FormData();
    formData.append("file", audioBlob, `recording-${Date.now()}.webm`);
    formData.append("userId", userId);
    formData.append("chatId", chatId);
    formData.append("model", selectedModel);

    try {
      setIsSending(true);
      setAudioBlob(null);
      onNewMessages([ {"role": "assistant", "message":"Voice message is sent ... Now wait for the Ai response ... this may take a while"}])
      const res = await fetch(`${API_BASE_URL}/api/save_voice_message`, {
        method: "POST",
        headers:{
            "authorization": `bearer ${token}`,
        },
        body: formData,
      });

      if (!res.ok) {
        setIsSending(false);
        throw new Error("Server error");
      }


      const data = await res.json();
      if (data.transcript == "") {
        setIsSending(false);
        window.alert("your Voice is not clear please make another audio record");
        return;
      };
      let transcript = data.transcript;
      const userMessage = {
        role: "user",
        message: "You said :   "+transcript
      };

      onNewMessages([userMessage]);
      setIsSending(false);

      setIsLoading(true);
      const aiRes = await fetch(`${API_BASE_URL}/api/get_ai_response`, {
        method: "POST",
        headers: {
          "authorization": `bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          userId,
          chatId,
          message: transcript,
          model: selectedModel,
          parameters: filterParameters(modelDetails, generationParams)
        }),
      });

      const reply = await readAIResponse(aiRes);

      const aiMessage = {
        role: 'assistant',
        message: reply
      };

      onNewMessages([aiMessage], true);


    } catch (err) {
      setIsSending(false);
      window.alert(err.message || "Failed to send the voice message.");
      console.error("Error:", err);
      return;
    } finally {
      setIsSending(false);
      setIsLoading(false);
    }
  };

  return (
    <div className="chat-container">
      <div className="voice-display" aria-live="polite">
        {isRecording ? (
          <span className="recording-indicator">🎤 Recording...</span>
        ) : (
          <span className="voice-idle">Record a question, then stop and send.</span>
        )}
        {audioUrl && <audio src={audioUrl} controls className="voice-audio" />}
      </div>

      <div className="voice-buttons">
        <button className="icon-button tools-button" onClick={startRecording} disabled={isRecording}>
          🎙️ <span>Start</span>
        </button>
        <button className="icon-button tools-button" onClick={stopRecording} disabled={!isRecording}>
          🛑 <span>Stop</span>
        </button>

        <button className="icon-button cancel-button" onClick={onCancel} aria-label="Cancel voice recording">
          ❌
        </button>
        <button
          className="icon-button send-button"
          onClick={sendVoice}
          disabled={!audioBlob || isSending}
          title={!audioBlob ? "Record something first" : "Send"}
        >
          ⬆️
        </button>
      </div>
    </div>
  );
}

export default VoiceMode;
