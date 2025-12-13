/**
 * GigiAI - Chat Module
 * Handles messaging, skeleton loaders, retry, copy
 * API: POST ${API_BASE}/assistant/api/chat/
 */

// ============================================
// MESSAGE MANAGEMENT
// ============================================

/**
 * Send message to AI
 * CRITICAL: Adds skeleton, handles retry
 */
async function sendMessage() {
    const input = document.getElementById('userInput');
    const sendBtn = document.getElementById('sendBtn');
    const sendBtnText = document.getElementById('sendBtnText');
    
    if (!input || !sendBtn) return;
    
    const message = input.value.trim();
    
    if (!message) {
        input.focus();
        return;
    }
    
    if (message.length > APP_CONFIG.maxMessageLength) {
        showToast(`Message too long (max ${APP_CONFIG.maxMessageLength} characters)`, 'warning');
        return;
    }
    
    // Add user message
    const messageId = `msg_${Date.now()}`;
    addMessage('user', message, messageId);
    
    // Clear input
    input.value = '';
    input.style.height = 'auto';
    
    AppState.messageCount++;
    
    // Show LinkedIn CTA after 3 messages
    if (AppState.messageCount === 3) {
        showLinkedInCTA();
    }
    
    // Disable send button
    sendBtn.disabled = true;
    sendBtnText.innerHTML = '<span class="spinner"></span>';
    
    // Update status
    updateStatus('thinking', 'Generating response...');
    
    // Show skeleton loader
    const skeletonId = `skeleton_${Date.now()}`;
    showSkeletonLoader(skeletonId);
    
    try {
        // API call - DO NOT MODIFY ENDPOINT
        const response = await fetch(`${API_BASE}/assistant/api/chat/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: AppState.sessionId,
                message: message
            })
        });
        
        // Remove skeleton
        removeSkeletonLoader(skeletonId);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.reply) {
            const cleanReply = stripMarkdown(data.reply);
            const aiMessageId = `msg_${Date.now()}`;
            addMessage('assistant', cleanReply, aiMessageId);
            updateStatus('connected', 'Connected');
            trackEvent('message_received', { length: data.reply.length });
        } else if (data.error) {
            addMessage('assistant', 'Sorry, I encountered an error processing your message.');
            updateStatus('error', 'Error occurred');
            trackEvent('message_error', { error: data.error });
        } else {
            throw new Error('Invalid response format');
        }
        
    } catch (error) {
        console.error('[Chat] Error:', error);
        removeSkeletonLoader(skeletonId);
        
        // Add failed message with retry
        const failedMessageId = `msg_${Date.now()}`;
        addFailedMessage(message, failedMessageId);
        
        updateStatus('error', 'Connection failed');
        showToast('Message failed to send. Click Retry to try again.', 'error', 5000);
        trackEvent('message_failed', { error: error.message });
    } finally {
        sendBtn.disabled = false;
        sendBtnText.textContent = 'Send';
        input.focus();
    }
}

/**
 * Retry failed message
 */
async function retryMessage(originalMessage, messageElement) {
    const retryBtn = messageElement.querySelector('.btn-retry');
    if (retryBtn) {
        retryBtn.disabled = true;
        retryBtn.innerHTML = '<span class="spinner"></span> Retrying...';
    }
    
    updateStatus('thinking', 'Retrying...');
    
    // Show skeleton
    const skeletonId = `skeleton_${Date.now()}`;
    showSkeletonLoader(skeletonId);
    
    try {
        const response = await fetch(`${API_BASE}/assistant/api/chat/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: AppState.sessionId,
                message: originalMessage
            })
        });
        
        removeSkeletonLoader(skeletonId);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.reply) {
            // Remove failed message
            messageElement.remove();
            
            // Add successful message
            const cleanReply = stripMarkdown(data.reply);
            const aiMessageId = `msg_${Date.now()}`;
            addMessage('assistant', cleanReply, aiMessageId);
            updateStatus('connected', 'Connected');
            showToast('Message sent successfully', 'success', 2000);
            trackEvent('message_retry_success');
        } else {
            throw new Error('Invalid response');
        }
        
    } catch (error) {
        console.error('[Retry] Error:', error);
        removeSkeletonLoader(skeletonId);
        
        if (retryBtn) {
            retryBtn.disabled = false;
            retryBtn.innerHTML = '<i class="bi bi-arrow-clockwise"></i> Retry';
        }
        
        updateStatus('error', 'Retry failed');
        showToast('Retry failed. Please try again.', 'error', 3000);
        trackEvent('message_retry_failed');
    }
}

/**
 * Add failed message with retry button
 */
function addFailedMessage(originalMessage, messageId) {
    const container = document.getElementById('chatMessages');
    if (!container) return;
    
    const messagesList = container.querySelector('.messages-list') || container;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant failed';
    messageDiv.id = messageId;
    messageDiv.setAttribute('data-original-message', originalMessage);
    
    const timestamp = formatTime();
    
    messageDiv.innerHTML = `
        <div class="message-bubble">
            <div class="message-content">
                <i class="bi bi-exclamation-triangle"></i> Message failed to send
            </div>
            <button class="btn-retry" onclick="retryMessage('${escapeForJs(originalMessage)}', document.getElementById('${messageId}'))">
                <i class="bi bi-arrow-clockwise"></i> Retry
            </button>
            <div class="message-footer">
                <span class="message-timestamp">${timestamp}</span>
            </div>
        </div>
    `;
    
    messagesList.appendChild(messageDiv);
    scrollToBottom();
}

// ============================================
// SKELETON LOADER
// ============================================

/**
 * Show skeleton loader while AI generates
 */
function showSkeletonLoader(skeletonId) {
    const container = document.getElementById('chatMessages');
    if (!container) return;
    
    const messagesList = container.querySelector('.messages-list') || container;
    
    const skeleton = document.createElement('div');
    skeleton.id = skeletonId;
    skeleton.className = 'message assistant';
    skeleton.innerHTML = `
        <div class="skeleton-bubble">
            <div class="skeleton-line"></div>
            <div class="skeleton-line"></div>
            <div class="skeleton-line"></div>
        </div>
    `;
    
    messagesList.appendChild(skeleton);
    scrollToBottom();
}

/**
 * Remove skeleton loader
 */
function removeSkeletonLoader(skeletonId) {
    const skeleton = document.getElementById(skeletonId);
    if (skeleton) {
        skeleton.remove();
    }
}

// ============================================
// MESSAGE RENDERING
// ============================================

/**
 * Add message to chat UI
 * @param {string} role - 'user' or 'assistant'
 * @param {string} content - Message content (HTML after sanitization)
 * @param {string} messageId - Unique message ID
 */
function addMessage(role, content, messageId) {
    const container = document.getElementById('chatMessages');
    if (!container) return;
    
    const messagesList = container.querySelector('.messages-list') || container;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    messageDiv.id = messageId;
    messageDiv.setAttribute('role', 'article');
    messageDiv.setAttribute('aria-label', `${role === 'user' ? 'Your' : 'Assistant'} message`);
    
    const timestamp = formatTime();
    
    // Strip HTML tags for plain text copy
    const plainText = content.replace(/<[^>]*>/g, '');
    
    let messageHTML = `
        <div class="message-bubble">
            <div class="message-content">${content}</div>
            <div class="message-footer">
                <span class="message-timestamp">${timestamp}</span>
                <div class="message-actions">
    `;
    
    // Copy button for all messages
    messageHTML += `
                    <button class="btn-icon" 
                            onclick="copyToClipboard('${escapeForJs(plainText)}')"
                            title="Copy message"
                            aria-label="Copy message">
                        <i class="bi bi-clipboard"></i>
                    </button>
    `;
    
    // TTS button for assistant messages
    if (role === 'assistant' && AppState.voiceEnabled) {
        messageHTML += `
                    <button class="btn-icon" 
                            onclick="playTTS(this, '${escapeForJs(plainText)}', '${messageId}')"
                            title="Play audio"
                            aria-label="Play audio">
                        <i class="bi bi-play-fill"></i>
                    </button>
        `;
    }
    
    messageHTML += `
                </div>
            </div>
        </div>
    `;
    
    messageDiv.innerHTML = messageHTML;
    messagesList.appendChild(messageDiv);
    scrollToBottom();
    
    trackEvent('message_added', { role, length: content.length });
}

// ============================================
// TYPING INDICATOR (Optional)
// ============================================

function showTypingIndicator() {
    const container = document.getElementById('chatMessages');
    if (!container) return;
    
    hideTypingIndicator();
    
    const messagesList = container.querySelector('.messages-list') || container;
    
    const indicator = document.createElement('div');
    indicator.id = 'typingIndicator';
    indicator.className = 'message assistant';
    indicator.innerHTML = `
        <div class="typing-indicator" aria-label="Assistant is typing" aria-live="polite">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
    `;
    
    messagesList.appendChild(indicator);
    scrollToBottom();
}

function hideTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) {
        indicator.remove();
    }
}

// ============================================
// QUICK ACTIONS
// ============================================

function handleQuickAction(text) {
    const input = document.getElementById('userInput');
    if (input) {
        input.value = text;
        sendMessage();
        trackEvent('quick_action_used', { text });
    }
}

// ============================================
// CHAT INITIALIZATION
// ============================================

/**
 * Start new chat session
 */
async function startChat() {
    if (!AppState.sessionId) {
        initSession();
    }
    
    updateStatus('thinking', 'Connecting...');
    
    // Show skeleton instead of typing indicator
    const skeletonId = `skeleton_${Date.now()}`;
    showSkeletonLoader(skeletonId);
    
    try {
        const response = await fetch(`${API_BASE}/assistant/api/chat/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: AppState.sessionId,
                message: 'Hello'
            })
        });
        
        removeSkeletonLoader(skeletonId);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.reply) {
            const cleanReply = stripMarkdown(data.reply);
            const messageId = `msg_${Date.now()}`;
            addMessage('assistant', cleanReply, messageId);
            updateStatus('connected', 'Connected');
            AppState.isConnected = true;
            trackEvent('chat_started');
        } else if (data.error) {
            addMessage('assistant', 'Sorry, I encountered an error. Please type your name and press Enter to continue.');
            updateStatus('error', 'Connection error');
            showToast('Connection hiccup — type your name to continue', 'warning', 5000);
        }
        
    } catch (error) {
        console.error('[Chat] Start error:', error);
        removeSkeletonLoader(skeletonId);
        addMessage('assistant', 'Connection failed. Please type your name and press Enter to retry.');
        updateStatus('error', 'Connection failed');
        showToast('Failed to connect — type your name to continue', 'error', 5000);
        trackEvent('chat_start_failed', { error: error.message });
    }
}

/**
 * Reset chat
 */
async function resetChat() {
    if (AppState.messageCount > 0) {
        const confirmed = confirm('Start a new conversation? This will clear current messages.');
        if (!confirmed) return;
    }
    
    const container = document.getElementById('chatMessages');
    if (container) {
        const messagesList = container.querySelector('.messages-list');
        if (messagesList) {
            messagesList.innerHTML = '';
        } else {
            container.innerHTML = '<div class="messages-list"></div>';
        }
    }
    
    AppState.messageCount = 0;
    AppState.isConnected = false;
    
    const linkedinCta = document.getElementById('linkedinCta');
    if (linkedinCta) {
        linkedinCta.style.display = 'none';
    }
    
    if (typeof stopTTS === 'function') {
        stopTTS();
    }
    
    initSession();
    await startChat();
    
    showToast('New conversation started', 'success', 2000);
    trackEvent('chat_reset');
}

// ============================================
// INPUT HANDLING
// ============================================

function handleInputKeypress(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

function autoResizeTextarea(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
}

// ============================================
// LINKEDIN CTA
// ============================================

function showLinkedInCTA() {
    const cta = document.getElementById('linkedinCta');
    if (cta && cta.style.display !== 'block') {
        cta.style.display = 'block';
        cta.style.animation = 'messageSlideIn 0.4s ease-out';
        trackEvent('linkedin_cta_shown');
    }
}

// ============================================
// EVENT LISTENERS
// ============================================

function setupChatListeners() {
    const input = document.getElementById('userInput');
    const sendBtn = document.getElementById('sendBtn');
    
    if (input) {
        input.addEventListener('keypress', handleInputKeypress);
        input.addEventListener('input', (e) => {
            autoResizeTextarea(e.target);
        });
    }
    
    if (sendBtn) {
        sendBtn.addEventListener('click', sendMessage);
    }
}

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    if (!document.getElementById('chatMessages')) return;
    
    console.log('[Chat] Initializing...');
    setupChatListeners();
    setTimeout(startChat, 500);
});
