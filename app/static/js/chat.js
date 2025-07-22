function addUserMessage(event) {
    const chatId = event.target.getAttribute("data-chat-id");
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message) return;

    const chatThread = document.getElementById('chat-thread-'+chatId);

    const userMessage = document.createElement('p');
    userMessage.innerHTML = `<strong>You:</strong> ${message}`;
    chatThread.appendChild(userMessage);
    input.value = '';
}

function clearChatThread(event) {
    const chatId = event.target.getAttribute("data-chat-id");
    const chatThread = document.getElementById('chat-thread-'+chatId);
    if (chatThread) {
        chatThread.innerHTML = "";
    }
    const chatName = document.getElementById('chat-name-'+chatId);
    if (chatName) {
        chatName.innerHTML = "";
    }
}