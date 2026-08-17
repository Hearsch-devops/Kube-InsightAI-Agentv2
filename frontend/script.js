
const chatForm = document.getElementById("chatForm");
const userInput = document.getElementById("userInput");
const chatBody = document.getElementById("chatBody");

// Backend API
const API_URL = "/api/chat";

// Keep track of conversation messages in the UI
const conversationHistory = [];

// Append message to chat UI
function appendMessage(sender, text) {
  const messageDiv = document.createElement("div");
  messageDiv.classList.add("message", `${sender}-message`);

  const contentDiv = document.createElement("div");
  contentDiv.classList.add("message-content");
  contentDiv.textContent = text;

  messageDiv.appendChild(contentDiv);
  chatBody.appendChild(messageDiv);

  // Auto-scroll to bottom
  chatBody.scrollTop = chatBody.scrollHeight;
}

// Show typing indicator
function showTypingIndicator() {
  const typingDiv = document.createElement("div");
  typingDiv.classList.add("message", "bot-message");
  typingDiv.id = "typingIndicator";

  const contentDiv = document.createElement("div");
  contentDiv.classList.add("message-content", "typing");
  contentDiv.innerHTML = "<span></span><span></span><span></span>";

  typingDiv.appendChild(contentDiv);
  chatBody.appendChild(typingDiv);

  chatBody.scrollTop = chatBody.scrollHeight;
}

// Remove typing indicator
function removeTypingIndicator() {
  const indicator = document.getElementById("typingIndicator");

  if (indicator) {
    indicator.remove();
  }
}

// Call CalcCast backend
async function fetchBotReply(userMessage) {
  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        message: userMessage
      })
    });

    if (!response.ok) {
      let errorMessage = "Backend request failed.";

      try {
        const errorData = await response.json();
        errorMessage =
          errorData.detail ||
          errorData.error ||
          errorMessage;
      } catch {
        // Ignore JSON parsing error
      }

      throw new Error(errorMessage);
    }

    const data = await response.json();

    if (!data.response) {
      throw new Error("Backend returned an empty response.");
    }

    return data.response;

  } catch (error) {
    console.error("CalcCast API Error:", error);

    return `Error: ${error.message}`;
  }
}

// Handle form submission
chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();

  const message = userInput.value.trim();

  if (!message) {
    return;
  }

  // Render user message
  appendMessage("user", message);

  // Store conversation locally
  conversationHistory.push({
    role: "user",
    content: message
  });

  // Clear input
  userInput.value = "";

  // Disable input while waiting
  userInput.disabled = true;

  // Show typing indicator
  showTypingIndicator();

  // Call backend
  const botReply = await fetchBotReply(message);

  // Remove typing indicator
  removeTypingIndicator();

  // Render bot response
  appendMessage("bot", botReply);

  // Store bot response locally
  conversationHistory.push({
    role: "assistant",
    content: botReply
  });

  // Re-enable input
  userInput.disabled = false;
  userInput.focus();
});