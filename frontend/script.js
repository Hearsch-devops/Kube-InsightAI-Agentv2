const chatForm = document.getElementById('chatForm');
const userInput = document.getElementById('userInput');
const chatBody = document.getElementById('chatBody');

// Append message to chat UI
function appendMessage(sender, text) {
  const messageDiv = document.createElement('div');
  messageDiv.classList.add('message', `${sender}-message`);

  const contentDiv = document.createElement('div');
  contentDiv.classList.add('message-content');
  contentDiv.textContent = text;

  messageDiv.appendChild(contentDiv);
  chatBody.appendChild(messageDiv);
  
  // Auto-scroll to bottom
  chatBody.scrollTop = chatBody.scrollHeight;
}

// Show typing indicator
function showTypingIndicator() {
  const typingDiv = document.createElement('div');
  typingDiv.classList.add('message', 'bot-message');
  typingDiv.id = 'typingIndicator';

  const contentDiv = document.createElement('div');
  contentDiv.classList.add('message-content', 'typing');
  contentDiv.innerHTML = `<span></span><span></span><span></span>`;

  typingDiv.appendChild(contentDiv);
  chatBody.appendChild(typingDiv);
  chatBody.scrollTop = chatBody.scrollHeight;
}

// Remove typing indicator
function removeTypingIndicator() {
  const indicator = document.getElementById('typingIndicator');
  if (indicator) {
    indicator.remove();
  }
}

// Handle Form Submission
chatForm.addEventListener('submit', (e) => {
  e.preventDefault();
  
  const message = userInput.value.trim();
  if (!message) return;

  // 1. Render User Message
  appendMessage('user', message);
  userInput.value = '';

  // 2. Show Typing Indicator
  showTypingIndicator();

  // 3. Simulate AI Bot Response (Replace this with real API call)
  setTimeout(() => {
    removeTypingIndicator();
    const botReply = generateBotReply(message);
    appendMessage('bot', botReply);
  }, 1200);
});

// Simple dummy reply logic
function generateBotReply(userText) {
  const lower = userText.toLowerCase();
  
  if (lower.includes('hello') || lower.includes('hi')) {
    return "Hello! How can I assist you today?";
  } else if (lower.includes('name')) {
    return "I'm your friendly AI Chatbot assistant.";
  } else if (lower.includes('help')) {
    return "I can answer questions, provide recommendations, or just chat with you!";
  } else {
    return `That's interesting! You said: "${userText}". How else can I help?`;
  }
}