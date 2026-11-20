def chat_summaries(chats):
    return [{"title": chat.get("title"), "chatId": str(chat.get("_id"))} for chat in chats]


def chat_messages(messages):
    return [{"role": message.get("role"), "message": message.get("content")} for message in messages]
