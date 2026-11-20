import { API_BASE_URL } from '../api';
import React, { useRef, useState, useEffect } from 'react';
import './ChatInput.css';
import ModelSelector from './Model_select';
import { useAuth } from '../authContext';
import VoiceMode from './VoiceMode';
import { filterParameters } from '../modelParameters';
import { readAIResponse } from '../aiResponse';

function ChatInput({ userId, chatId, selectedModel, onModelChange, generationParams, modelDetails, onNewMessages, setIsLoading }) {
  const [message, setMessage] = useState('');
  const [showModels, setShowModels] = useState(false);
  const sendingRef = useRef(false);
  const [sending, setSending] = useState(false);
  const [ToggleVocal, setToggleVocal] = useState(false)

  const { token } = useAuth();

  const textareaRef = useRef(null);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      const lineHeight = 24;
      const maxLines = 4;
      const maxHeight = lineHeight * maxLines;
      textarea.style.height = `${Math.min(textarea.scrollHeight, maxHeight)}px`;
      textarea.scrollTop = textarea.scrollHeight;
    }
  }, [message]);

  const handleSend = async () => {
    if (!message.trim() || sendingRef.current) return;

    const userMessage = { role: 'user', message };

    try {
      if (selectedModel == "no_model") {
        window.alert("click on Model and select a model");
        return;
      }
      sendingRef.current = true;
      setSending(true);
      const res = await fetch(`${API_BASE_URL}/api/save_message_ai/`, {
        method: "POST",
        headers: {
          "authorization": `bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          chatId,
          userId,
          message,
          model: selectedModel// include selected model in the body
        }),
      });

      if (!res.ok) {
        throw new Error("Failed to send message")
      }

      setMessage(""); // clear input
      onNewMessages([userMessage])

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
          message,
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
      window.alert(err.message || "Failed to get an AI response.");
      console.error("Error:", err);
    } finally {
      sendingRef.current = false;
      setSending(false);
      setIsLoading(false);
    }
  };

  const handleModelClick = () => {
    setShowModels((prev) => !prev);
  };

  const handleVocalMessage = () => {
    setToggleVocal(prev => !prev);
  }

  const handleNewMessages = (newMessage, done) => {
    onNewMessages(newMessage, done);
  };

  const handleLoading = (state) => {
    setIsLoading(state)
  }

  return (
    <div className="chat-container">
      <button className="icon-button tools-button" onClick={handleModelClick}>
        ⚙️ <span>Model</span>
      </button>

      {showModels && (
        <ModelSelector
          selectedModel={selectedModel}
          onModelChange={onModelChange}
        />
      )}


      {!ToggleVocal ? (
        <>
          <textarea
            ref={textareaRef}
            className="chat-textarea"
            placeholder="Ask anything"
            aria-label="Message"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            rows={1}
          />


          <button className="icon-button voice-button" onClick={handleVocalMessage} aria-label="Record a voice message" disabled={sending}>🎤</button>
          <button className="icon-button send-button" onClick={handleSend} aria-label="Send message" disabled={sending || !message.trim()}>
            ⬆️
          </button>
        </>) :
        <VoiceMode onCancel={() => setToggleVocal(false)} onNewMessages={handleNewMessages} setIsLoading={handleLoading}
          userId={userId}
          chatId={chatId}
          selectedModel={selectedModel}
          modelDetails={modelDetails}
          generationParams={generationParams} />
      }
    </div>
  );
}

export default ChatInput;
