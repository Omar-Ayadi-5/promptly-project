import NewChatImage from "./images/new_chat.png";
import "../FullStyle.css";
import HistoryChatsName from "./HistoryChat";
import DeleteBin from "./images/delete_bin.png";
import React, { useState } from "react";

function SideBar({ isVisible, onChatSelect, onNewChatClick, refreshFlag, selectedChatId, onChatDeleted }) {


    const [DeleteShow, SetDeleteShow] = useState(false)
    return (
        <aside className={`sidebar ${isVisible ? "slide-in" : "slide-out"}`}>
            <button className="new_delete-chat-button" onClick={onNewChatClick}>
                <p>New chat</p>
                <img src={NewChatImage} width={20} alt="New Chat" />
            </button>
            <button className="new_delete-chat-button" onClick={() => SetDeleteShow(!DeleteShow)}>
                <p>{DeleteShow ? "Cancel Delete" : "Delete chat"}</p>
                <img src={DeleteBin} id="imgH" width={15} alt="Delete" />
            </button>
            <div className="chat-links">
                <p className="sidebar-title">Chats</p>
                <HistoryChatsName
                    onChatSelect={onChatSelect}
                    deleteMode={DeleteShow}
                    refreshFlag={refreshFlag}
                    selectedChatId={selectedChatId}
                    onChatDeleted={onChatDeleted}
                />

            </div>
        </aside>
    );
}


export default SideBar;
