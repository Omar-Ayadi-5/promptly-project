import { API_BASE_URL } from '../api';
import { useCallback, useEffect, useState } from "react";
import "../FullStyle.css";
import DeleteBin from "./images/delete_bin.png";
import { useAuth } from "../authContext"; // <-- Make sure the path is correct

const HistoryChatsName = ({ deleteMode, onChatSelect, refreshFlag, selectedChatId, onChatDeleted }) => {
    const {userId, token } = useAuth();
    const [loading, setLoading] = useState(true);
    const [chatData, setChatData] = useState([]);

    const fetchChats = useCallback(async () => {
        try {
            setLoading(true);
            const response = await fetch(`${API_BASE_URL}/api/Load_chats_name/${userId}`, {
                method: "GET",
                headers: {
                    "authorization": `bearer ${token}`,
                    "Content-Type": "application/json"
                }
            });
            if (!response.ok) throw new Error("Erreur réseau");
            const data = await response.json();
            setChatData(data);

        } catch (error) {
            console.error("Erreur lors du chargement des données:", error);
            setChatData([]);
        } finally {
            setLoading(false);
        }
    }, [userId, token]);

    useEffect(() => {
        if (userId) fetchChats();
    }, [userId, refreshFlag, fetchChats]);

    const handleDelete = async (chatId) => {
        if (!window.confirm("Are you sure you want to delete this chat?")) return;
        try {
            const response = await fetch(`${API_BASE_URL}/api/delete_chat`, {
                method: "DELETE",
                headers: {
                    "authorization": `bearer ${token}`,
                    "Content-Type": "application/json"
                },
                body:JSON.stringify({
                    userId,
                    chatId
                })
            });
            if (!response.ok) throw new Error("Failed to delete");
            setChatData(prev => prev.filter(chat => chat.chatId !== chatId));
            if (selectedChatId === chatId) {
                onChatDeleted(); // Reset the selected chat
            }

        } catch (err) {
            console.error("Delete failed", err);
        }
    };

    if (loading) return <p>Loading chats...</p>;

    return (
        <div>
            {chatData.map((chat, index) => (
                <div className="chat-item-container" key={index}>
                    <button
                        className="chat-button"
                        onClick={() => !deleteMode && onChatSelect(chat.title, chat.chatId, userId)}
                    >
                        <p>{chat.title}</p>
                    </button>
                    {deleteMode && (
                        <button
                            className="delete-icon"
                            onClick={() => handleDelete(chat.chatId)}
                        >
                            <img src={DeleteBin} id="imgH" width={15} alt="Delete" />
                        </button>
                    )}
                </div>
            ))}
        </div>
    );
};

export default HistoryChatsName;
