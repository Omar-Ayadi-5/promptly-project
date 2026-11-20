import { API_BASE_URL } from './api';
import Chat_input from "./components/Chat_input";
import Profile from "./components/images/profil.png";
import SideImage from "./components/images/menu.png";
import models_Nav_Img from "./components/images/models_nav_img.png"
import "./FullStyle.css";
import { useState, useEffect, useRef } from "react";
import SideBar from "./components/SideBar";
import NewChat from "./components/MakeNewChat";
import ModelsNav from "./components/ModelsNav";
import ReactMarkdown from 'react-markdown'; //used for styling the messages getted from the ai to be shown correctly
import ShowProfile from "./components/ProfileSettings";
import { useAuth } from "./authContext";
import useModelParameters from './useModelParameters';


function Content() {
    const { userId, token } = useAuth();


    const [showSidebar, setShowSidebar] = useState(() => window.innerWidth >= 900);
    const [shouldRenderSidebar, setShouldRenderSidebar] = useState(() => window.innerWidth >= 900);

    const [showNavbar, setShowNavbar] = useState(false);
    const [shouldRenderNavbar, setShouldRenderNavbar] = useState(false);

    const [selectedModel, setSelectedModel] = useState('no_model');

    const { model, generationParams, draftParams, changeDraft, applyParameters } =
        useModelParameters(selectedModel, token);


    const [selectedChat, setSelectedChat] = useState(null);

    const [messages, setMessages] = useState([]);


    const [showNewChatModal, setShowNewChatModal] = useState(false);

    const [refreshChatsFlag, setRefreshChatsFlag] = useState(false);

    const [chatId, setChatId] = useState(null);

    const [isLoading, setIsLoading] = useState(false);

    const [ProfileShow, setProfileShow] = useState(false)


    const refreshChatList = () => {
        setRefreshChatsFlag(prev => !prev);
    };
    const handleShowbar = () => {
        if (!showSidebar) {
            setShouldRenderSidebar(true);
            setShowSidebar(true);
        } else {
            setShowSidebar(false);
            setTimeout(() => setShouldRenderSidebar(false), 300);
        }
    };
    const handleshowNavbar = () => {
        if (!showNavbar) {
            setShouldRenderNavbar(true);
            setShowNavbar(true);
        } else {
            setShowNavbar(false);
            setTimeout(() => setShouldRenderNavbar(false), 300); // match animation duration
        }
    };
    const handleshowProfile = () => {
        if (!ProfileShow) {
            setProfileShow(true);
        }
        else {
            setProfileShow(false);
        }
    }

    const clearSelectedChat = () => {
        setSelectedChat(null);
        setChatId(null);
        setMessages([]);
    };


    // Handle chat selection
    const handleChatSelect = async (chatTitle, chatId, userId) => {
        setSelectedChat(chatTitle);
        setChatId(chatId)
        try {

            const response = await fetch(`${API_BASE_URL}/api/Load_chat_messages/${userId}/${chatId}`,{
            method : "GET",
            headers :{
                "authorization": `bearer ${token}`,
                'Content-Type': 'application/json'
            }

            });

            const data = await response.json();
            if (!response.ok || !Array.isArray(data)) throw new Error(data.error || "Unable to load messages");
            setMessages(data.map(message => ({ ...message, role: message.role === 'AI' ? 'assistant' : message.role })));
            if (window.innerWidth < 900) {
                setShowSidebar(false);
                setShouldRenderSidebar(false);
            }
        } catch (error) {
            console.error("Failed to load messages:", error);
            setMessages([]);
        }
    };
    const profileRef = useRef();

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (profileRef.current && !profileRef.current.contains(event.target)) {
                setProfileShow(false);
            }
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);


    return (
        <main className={`workspace ${shouldRenderSidebar ? 'sidebar-open' : ''} ${shouldRenderNavbar ? 'parameters-open' : ''}`}>
            <header>
                <button onClick={handleShowbar} aria-label="Toggle chat history" aria-expanded={showSidebar}>
                    <img src={SideImage} width={30} className="header-left" alt="Menu" />
                </button>

                <div className="header-left" id="plName">Promptly</div>

                <div className="header-right">
                    <button onClick={handleshowNavbar} aria-label="Model parameters" aria-expanded={showNavbar}>
                        <img src={models_Nav_Img} width={35} alt="" />
                    </button>
                    <button onClick={handleshowProfile} aria-label="Account menu" aria-expanded={ProfileShow}>
                        <img src={Profile} className="profile" alt="Profile" />
                    </button>


                </div>
            </header>

            {shouldRenderNavbar && <ModelsNav
                isVisible={showNavbar}
                selectedModel={model}
                parameters={draftParams}
                onDraftChange={changeDraft}
                onParamsChange={applyParameters}
            />

            }


            {shouldRenderSidebar && (
                <SideBar
                    isVisible={showSidebar}
                    onChatSelect={handleChatSelect}
                    onNewChatClick={() => setShowNewChatModal(true)}
                    refreshFlag={refreshChatsFlag}
                    selectedChatId={chatId}
                    onChatDeleted={clearSelectedChat}
                />
            )}

            {showNewChatModal && (
                <NewChat onClose={() => setShowNewChatModal(false)}
                    onChatAdded={refreshChatList}
                />
            )}

            {ProfileShow && (
                <div ref={profileRef}>
                    <ShowProfile

                    />
                </div>
            )}


            <div className="chat-scroll">
                <section>
                    <div id="chat">
                        {selectedChat ? (
                            <>
                                <h2>{selectedChat}</h2> <br />
                                {messages.length > 0 ? (
                                    messages.map((msg, index) => (
                                        <div key={index} className={`message ${msg.role}`}>
                                            <h4>{msg.role === "user" ? "You" : "Assistant"}</h4>
                                            <ReactMarkdown>{msg.message}</ReactMarkdown>
                                            <br /><br />
                                        </div>

                                    ))
                                ) : (
                                    <p>No messages in this chat yet.</p>
                                )}

                            </>
                        ) : (
                            <div className="welcome-state">
                                <span className="eyebrow">YOUR AI WORKSPACE</span>
                                <h1>A fresh perspective starts here.</h1>
                                <p>Explore ideas, work through a problem, or follow your curiosity.</p>
                                <button className="primary-action" onClick={() => setShowNewChatModal(true)}>Start a conversation</button>
                                <div className="welcome-features">
                                    <div><strong>Choose your model</strong><span>Find a different perspective.</span></div>
                                    <div><strong>Make it your own</strong><span>Fine-tune how your model responds.</span></div>
                                    <div><strong>Pick up where you left off</strong><span>Your conversations stay together.</span></div>
                                </div>
                            </div>
                        )}
                        {isLoading && (
                            <div className="message assistant loading">
                                <p><em>Loading AI response...</em></p>
                            </div>
                        )}

                    </div>
                </section>
            </div>

            <footer>
                {chatId && (
                    <Chat_input
                        userId={userId}
                        chatId={chatId}
                        selectedModel={selectedModel}
                        onModelChange={setSelectedModel}
                        generationParams={generationParams}
                        modelDetails={model}
                        onNewMessages={(newMessages, done = true) => {
                            setMessages(prev => [...prev, ...newMessages]);
                            if (done) setIsLoading(false);
                        }}
                        setIsLoading={setIsLoading}
                    />
                )}


            </footer>
        </main>
    );
}

export default Content;
