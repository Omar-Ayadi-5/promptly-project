import { API_BASE_URL } from '../api';
import { useState } from "react";
import "./NewChat.css";
import { useAuth } from "../authContext";

const NewChat = ({ onClose, onChatAdded }) => {
  const [chatTitle, setChatTitle] = useState("");
  const [showWarning, setShowWarning] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const {userId,token} =useAuth();


  const handleOkClick = () => {
    if (chatTitle.trim() === "") {
      setShowWarning(true);
      return;
    }

    if (saving) return;
    setSaving(true);
    setError("");
    setShowWarning(false);

    //  Only one fetch here, including user_id
    fetch(`${API_BASE_URL}/api/add_new_title`, {
      method: "POST",
      headers: {
         "authorization": `bearer ${token}`,
         "Content-Type": "application/json" },
      body: JSON.stringify({ title: chatTitle.trim(), user_id: userId }),
    })
      .then((res) => {
        if (res.ok) {
          onChatAdded();
          onClose(); //  Close only if saved
        } else {
          setError("Unable to create the chat. Please try again.");
        }
      })
      .catch(() => setError("Unable to connect. Please try again."))
      .finally(() => setSaving(false));
  };

  return (
    <div className="modal-overlay">
      <div className="modal-box" role="dialog" aria-modal="true" aria-labelledby="new-chat-title" onKeyDown={event => { if (event.key === "Escape") onClose(); }}>
        <h2 id="new-chat-title">New conversation</h2>
        <p>Add new chat</p>
        <input
          placeholder="What would you like to explore?"
          aria-label="Chat title"
          maxLength={100}
          autoFocus
          type="text"
          value={chatTitle}
          onChange={(e) => {
            setChatTitle(e.target.value);
            if (showWarning) setShowWarning(false);
          }}
        />
        {showWarning && <p className="warning">Please enter a chat title.</p>}
        {error && <p role="alert">{error}</p>}
        <div className="modal-actions"><button className="modal-cancel" onClick={onClose} disabled={saving}>Cancel</button><button onClick={handleOkClick} disabled={saving}>{saving ? "Creating..." : "Create chat"}</button></div>
      </div>
    </div>
  );
};

export default NewChat;
