/**
 * Petrosia Chat Widget
 * Embeddable customer support chat widget with streaming RAG responses
 * 
 * Usage: <script src="https://your-domain/widget.js" data-api-url="http://localhost:8000"></script>
 */

(function() {
  'use strict';

  // Configuration
  const script = document.currentScript;
  const API_URL = script.getAttribute('data-api-url') || 'http://localhost:8000';
  const POSITION = script.getAttribute('data-position') || 'bottom-right';
  const PRIMARY_COLOR = script.getAttribute('data-color') || '#0066FF';

  // Create widget HTML
  const widgetHTML = `
    <div id="petrosia-widget" class="petrosia-widget petrosia-${POSITION}">
      <!-- Floating bubble -->
      <div id="petrosia-bubble" class="petrosia-bubble">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M20 2H4C2.9 2 2 2.9 2 4V22L6 18H20C21.1 18 22 17.1 22 16V4C22 2.9 21.1 2 20 2ZM20 16H6L4 18V4H20V16Z" fill="white"/>
        </svg>
        <div class="petrosia-bubble-badge" id="petrosia-badge" style="display:none;">1</div>
      </div>

      <!-- Chat window -->
      <div id="petrosia-window" class="petrosia-window" style="display:none;">
        <div class="petrosia-header">
          <div class="petrosia-header-title">
            <h3>Ask Petrosia</h3>
            <p>How can we help you?</p>
          </div>
          <button id="petrosia-close" class="petrosia-close">×</button>
        </div>
        
        <div id="petrosia-messages" class="petrosia-messages">
          <div class="petrosia-message petrosia-message-bot">
            <div class="petrosia-message-content">
              <p>👋 Hi! I'm Petrosia, your support assistant. Ask me anything from our knowledge base.</p>
            </div>
          </div>
        </div>

        <div class="petrosia-input-container">
          <textarea 
            id="petrosia-input" 
            class="petrosia-input" 
            placeholder="Type your question..."
            rows="1"
          ></textarea>
          <button id="petrosia-send" class="petrosia-send">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M2 10L18 2L10 18L8 11L2 10Z" fill="currentColor"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
  `;

  // Inject CSS
  const style = document.createElement('style');
  style.textContent = `
    .petrosia-widget {
      position: fixed;
      z-index: 9999;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    }
    
    .petrosia-bottom-right { bottom: 20px; right: 20px; }
    .petrosia-bottom-left { bottom: 20px; left: 20px; }
    
    .petrosia-bubble {
      width: 60px;
      height: 60px;
      border-radius: 50%;
      background: ${PRIMARY_COLOR};
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      transition: transform 0.2s, box-shadow 0.2s;
      position: relative;
    }
    
    .petrosia-bubble:hover {
      transform: scale(1.1);
      box-shadow: 0 6px 16px rgba(0,0,0,0.2);
    }
    
    .petrosia-bubble-badge {
      position: absolute;
      top: -4px;
      right: -4px;
      background: #FF3B30;
      color: white;
      border-radius: 10px;
      padding: 2px 6px;
      font-size: 12px;
      font-weight: bold;
    }
    
    .petrosia-window {
      width: 380px;
      height: 600px;
      max-height: calc(100vh - 100px);
      background: white;
      border-radius: 12px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.2);
      display: flex;
      flex-direction: column;
      position: absolute;
      bottom: 80px;
      right: 0;
      animation: petrosia-slide-up 0.3s ease-out;
    }
    
    @keyframes petrosia-slide-up {
      from {
        opacity: 0;
        transform: translateY(20px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }
    
    .petrosia-header {
      background: ${PRIMARY_COLOR};
      color: white;
      padding: 20px;
      border-radius: 12px 12px 0 0;
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
    }
    
    .petrosia-header-title h3 {
      margin: 0;
      font-size: 18px;
      font-weight: 600;
    }
    
    .petrosia-header-title p {
      margin: 4px 0 0 0;
      font-size: 13px;
      opacity: 0.9;
    }
    
    .petrosia-close {
      background: none;
      border: none;
      color: white;
      font-size: 32px;
      cursor: pointer;
      padding: 0;
      width: 32px;
      height: 32px;
      line-height: 28px;
      opacity: 0.8;
      transition: opacity 0.2s;
    }
    
    .petrosia-close:hover {
      opacity: 1;
    }
    
    .petrosia-messages {
      flex: 1;
      overflow-y: auto;
      padding: 20px;
      background: #F5F5F7;
    }
    
    .petrosia-message {
      margin-bottom: 16px;
      animation: petrosia-fade-in 0.3s ease-out;
    }
    
    @keyframes petrosia-fade-in {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }
    
    .petrosia-message-content {
      background: white;
      padding: 12px 16px;
      border-radius: 18px;
      max-width: 80%;
      box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    
    .petrosia-message-user .petrosia-message-content {
      background: ${PRIMARY_COLOR};
      color: white;
      margin-left: auto;
    }
    
    .petrosia-message-content p {
      margin: 0;
      font-size: 14px;
      line-height: 1.5;
    }
    
    .petrosia-sources {
      margin-top: 12px;
      padding: 8px 12px;
      background: #F0F0F2;
      border-radius: 8px;
      font-size: 12px;
    }
    
    .petrosia-sources-title {
      font-weight: 600;
      margin-bottom: 4px;
      color: #666;
    }
    
    .petrosia-source-link {
      display: block;
      color: ${PRIMARY_COLOR};
      text-decoration: none;
      margin-top: 4px;
    }
    
    .petrosia-typing {
      display: flex;
      gap: 4px;
      padding: 12px 16px;
    }
    
    .petrosia-typing-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #999;
      animation: petrosia-typing 1.4s infinite;
    }
    
    .petrosia-typing-dot:nth-child(2) { animation-delay: 0.2s; }
    .petrosia-typing-dot:nth-child(3) { animation-delay: 0.4s; }
    
    @keyframes petrosia-typing {
      0%, 60%, 100% { opacity: 0.3; }
      30% { opacity: 1; }
    }
    
    .petrosia-input-container {
      display: flex;
      padding: 16px;
      background: white;
      border-top: 1px solid #E5E5E7;
      gap: 8px;
    }
    
    .petrosia-input {
      flex: 1;
      border: 1px solid #E5E5E7;
      border-radius: 20px;
      padding: 10px 16px;
      font-size: 14px;
      resize: none;
      outline: none;
      font-family: inherit;
      max-height: 100px;
    }
    
    .petrosia-input:focus {
      border-color: ${PRIMARY_COLOR};
    }
    
    .petrosia-send {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      background: ${PRIMARY_COLOR};
      border: none;
      color: white;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: transform 0.2s;
    }
    
    .petrosia-send:hover {
      transform: scale(1.1);
    }
    
    .petrosia-send:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
  `;
  document.head.appendChild(style);

  // Inject widget into page
  const container = document.createElement('div');
  container.innerHTML = widgetHTML;
  document.body.appendChild(container.firstElementChild);

  // Get elements
  const bubble = document.getElementById('petrosia-bubble');
  const chatWindow = document.getElementById('petrosia-window');
  const closeBtn = document.getElementById('petrosia-close');
  const input = document.getElementById('petrosia-input');
  const sendBtn = document.getElementById('petrosia-send');
  const messages = document.getElementById('petrosia-messages');

  let isOpen = false;

  // Toggle chat window
  function toggleWindow() {
    isOpen = !isOpen;
    chatWindow.style.display = isOpen ? 'flex' : 'none';
    if (isOpen) {
      input.focus();
    }
  }

  bubble.addEventListener('click', toggleWindow);
  closeBtn.addEventListener('click', toggleWindow);

  // Auto-resize textarea
  input.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 100) + 'px';
  });

  // Send message on Enter (Shift+Enter for new line)
  input.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  sendBtn.addEventListener('click', sendMessage);

  // Add message to chat
  function addMessage(content, isUser = false, sources = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `petrosia-message petrosia-message-${isUser ? 'user' : 'bot'}`;
    
    let messageHTML = `
      <div class="petrosia-message-content">
        <p>${escapeHtml(content)}</p>
      </div>
    `;

    if (sources && sources.length > 0) {
      messageHTML += `
        <div class="petrosia-sources">
          <div class="petrosia-sources-title">📚 Sources:</div>
          ${sources.map(s => `<a href="#" class="petrosia-source-link">${s.title}</a>`).join('')}
        </div>
      `;
    }

    messageDiv.innerHTML = messageHTML;
    messages.appendChild(messageDiv);
    messages.scrollTop = messages.scrollHeight;
  }

  // Add typing indicator
  function addTypingIndicator() {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'petrosia-message petrosia-message-bot';
    typingDiv.id = 'petrosia-typing';
    typingDiv.innerHTML = `
      <div class="petrosia-message-content petrosia-typing">
        <div class="petrosia-typing-dot"></div>
        <div class="petrosia-typing-dot"></div>
        <div class="petrosia-typing-dot"></div>
      </div>
    `;
    messages.appendChild(typingDiv);
    messages.scrollTop = messages.scrollHeight;
  }

  function removeTypingIndicator() {
    const typing = document.getElementById('petrosia-typing');
    if (typing) typing.remove();
  }

  // Send message to API
  async function sendMessage() {
    const query = input.value.trim();
    if (!query) return;

    // Add user message
    addMessage(query, true);
    input.value = '';
    input.style.height = 'auto';

    // Disable input while processing
    sendBtn.disabled = true;
    input.disabled = true;
    addTypingIndicator();

    try {
      // Call streaming API
      const response = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: query,
          language: window.PETROSIA_LANGUAGE || 'auto',
          provider: null  // Use default
        })
      });

      if (!response.ok) {
        throw new Error('Failed to get response');
      }

      removeTypingIndicator();

      // Create message for streaming response
      const messageDiv = document.createElement('div');
      messageDiv.className = 'petrosia-message petrosia-message-bot';
      messageDiv.innerHTML = '<div class="petrosia-message-content"><p></p></div>';
      messages.appendChild(messageDiv);
      const contentP = messageDiv.querySelector('p');

      // Stream response
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullResponse = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') break;
            if (data.startsWith('[ERROR]')) {
              contentP.textContent = 'Sorry, I encountered an error. Please try again.';
              break;
            }
            fullResponse += data;
            contentP.textContent = fullResponse;
            messages.scrollTop = messages.scrollHeight;
          }
        }
      }

    } catch (error) {
      removeTypingIndicator();
      addMessage('Sorry, I encountered an error. Please try again.', false);
      console.error('Chat error:', error);
    } finally {
      sendBtn.disabled = false;
      input.disabled = false;
      input.focus();
    }
  }

  // Utility: Escape HTML
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  console.log('✅ Petrosia widget loaded');
})();
