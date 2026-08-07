// DOM Elements
const form = document.getElementById('chat-form');
const input = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const chatWindow = document.getElementById('chat-window');
const welcomeScreen = document.getElementById('welcome-screen');
const typingIndicator = document.getElementById('typing-indicator');
const newChatBtn = document.getElementById('new-chat-btn');
const clearChatBtn = document.getElementById('clear-chat-btn');
const errorToast = document.getElementById('error-toast');
const devModeToggle = document.getElementById('dev-mode-checkbox');
const devInfoPanel = document.getElementById('dev-info-panel');

// Developer Panel Elements
const devSessionId = document.getElementById('dev-session-id');
const devFlow = document.getElementById('dev-flow');
const devStage = document.getElementById('dev-stage');
const devIntent = document.getElementById('dev-intent');
const devConfidence = document.getElementById('dev-confidence');

// State
let sessionId = localStorage.getItem('naheed_session_id');
let isProcessing = false;

// Initialize
function init() {
    if (!sessionId) {
        sessionId = generateUUID();
        localStorage.setItem('naheed_session_id', sessionId);
    }
    devSessionId.textContent = sessionId.split('-')[0] + '...';
    
    // Auto-resize textarea
    input.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 200) + 'px';
        if (this.value.trim() === '') {
            this.style.height = 'auto';
        }
    });

    // Handle Shift+Enter
    input.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!isProcessing && this.value.trim() !== '') {
                form.dispatchEvent(new Event('submit'));
            }
        }
    });
}

// Generate UUID
function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

// Show Error
function showError(msg) {
    errorToast.textContent = msg;
    errorToast.classList.remove('hidden');
    setTimeout(() => { errorToast.classList.add('hidden'); }, 3000);
}

// Scroll to bottom
function scrollToBottom() {
    chatWindow.scrollTo({
        top: chatWindow.scrollHeight,
        behavior: 'smooth'
    });
}

// Format Time
function formatTime() {
    return new Intl.DateTimeFormat('en-US', { hour: 'numeric', minute: 'numeric', hour12: true }).format(new Date());
}

// Sanitize HTML and Parse Markdown-like text
function formatText(str) {
    // Escape HTML first
    let text = str.replace(/[&<>'"]/g, 
        tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[tag] || tag)
    );
    
    // Basic markdown for messages
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    text = text.replace(/\n/g, '<br>');
    return text;
}

// Add Message to DOM
function appendMessage(role, text) {
    if (!welcomeScreen.classList.contains('hidden')) {
        welcomeScreen.classList.add('hidden');
    }

    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;
    
    let innerHTML = '';
    if (role === 'bot') {
        innerHTML += `<div class="bot-avatar"><i data-lucide="bot" style="width:20px;height:20px"></i></div>`;
    }
    
    innerHTML += `
        <div class="bubble-container">
            <div class="bubble">${formatText(text)}</div>
            <span class="timestamp">${formatTime()}</span>
        </div>
    `;
    
    msgDiv.innerHTML = innerHTML;
    chatWindow.appendChild(msgDiv);
    
    // Move typing indicator to bottom
    chatWindow.appendChild(typingIndicator);
    scrollToBottom();
    
    // Re-initialize icons for newly added DOM elements
    if (window.lucide) {
        lucide.createIcons();
    }
}

// Update Dev Panel
function updateDevPanel(debugData) {
    if (!debugData) return;
    if (debugData.flow_status) devFlow.textContent = debugData.flow_status;
    if (debugData.intent) devIntent.textContent = debugData.intent;
    if (debugData.confidence) devConfidence.textContent = debugData.confidence;
}

// Toggle UI Processing State
function setProcessing(processing) {
    isProcessing = processing;
    input.disabled = processing;
    sendBtn.disabled = processing;
    if (processing) {
        typingIndicator.classList.remove('hidden');
        chatWindow.appendChild(typingIndicator);
        scrollToBottom();
    } else {
        typingIndicator.classList.add('hidden');
        input.focus();
    }
}

// Form Submit Handler
form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const message = input.value.trim();
    if (!message || isProcessing) return;

    input.value = '';
    input.style.height = 'auto';
    
    appendMessage('user', message);
    setProcessing(true);

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId, message: message })
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || 'Network error');
        }

        const data = await response.json();
        
        // Slight artificial delay to ensure typing animation plays
        setTimeout(() => {
            setProcessing(false);
            appendMessage('bot', data.response);
            updateDevPanel(data.debug);
            
            // End chat on goodbye
            if (data.debug && data.debug.intent === 'goodbye') {
                input.disabled = true;
                sendBtn.disabled = true;
                input.placeholder = "Chat ended. Please click 'New Chat' to start again.";
                isProcessing = true; // Prevent shift+enter bypass
            }
        }, 300);

    } catch (error) {
        setProcessing(false);
        showError('Connection failed. Please try again.');
        console.error(error);
    }
});

// Clear Chat Action
async function clearChat() {
    try {
        await fetch('/api/clear', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId })
        });
    } catch (e) {
        console.error('Failed to clear state on server', e);
    }
    
    // Clear DOM
    const messages = chatWindow.querySelectorAll('.message');
    messages.forEach(m => m.remove());
    welcomeScreen.classList.remove('hidden');
    devFlow.textContent = 'None';
    devIntent.textContent = 'None';
    
    // Restore input state
    input.disabled = false;
    sendBtn.disabled = false;
    input.placeholder = "Message Naheed Support...";
    isProcessing = false;
}

clearChatBtn.addEventListener('click', clearChat);

// New Chat Action (Generates new Session ID)
newChatBtn.addEventListener('click', async () => {
    sessionId = generateUUID();
    localStorage.setItem('naheed_session_id', sessionId);
    devSessionId.textContent = sessionId.split('-')[0] + '...';
    
    // Visually clear chat
    const messages = chatWindow.querySelectorAll('.message');
    messages.forEach(m => m.remove());
    welcomeScreen.classList.remove('hidden');
    devFlow.textContent = 'None';
    devIntent.textContent = 'None';
    
    // Restore input state
    input.disabled = false;
    sendBtn.disabled = false;
    input.placeholder = "Message Naheed Support...";
    isProcessing = false;
});

// Dev Mode Toggle
devModeToggle.addEventListener('change', (e) => {
    if (e.target.checked) {
        devInfoPanel.classList.remove('hidden');
    } else {
        devInfoPanel.classList.add('hidden');
    }
});

init();
