function addUserMessage(event) {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message) return;

    const chatThread = document.getElementById('chat-thread');

    const userMessage = document.createElement('p');
    userMessage.innerHTML = `<strong>You:</strong> ${message}`;
    chatThread.appendChild(userMessage);
    input.value = '';
}

function clearChatThread() {
    const chatThread = document.getElementById('chat-thread');
    chatThread.innerHTML = "";
    const chatName = document.getElementById('chat-name');
    chatName.innerHTML = "";
}