const MESSAGE_TEXTS = new Map();

function getMessageText(messageId) {
    return MESSAGE_TEXTS.get(messageId);
}

function playTTSById(messageId) {
    const text = MESSAGE_TEXTS.get(messageId);
    if (!text) {
        console.error('[TTS] No text for message:', messageId);
        return;
    }

    const button = document.querySelector(`#${messageId} .btn-icon[onclick*="playTTSById"]`);
    if (!button) {
        console.error('[TTS] Button not found:', messageId);
        return;
    }

    if (typeof playTTS === 'function') {
        playTTS(button, text, messageId);
    } else {
        console.error('[TTS] playTTS not found');
    }
}

function autoPlayTTSForMessage(messageId) {
    if (typeof getTTSSettings === 'function') {
        const settings = getTTSSettings();
        if (!settings.autoPlay || !settings.enabled) return;
    } else if (!AppState.voiceEnabled) {
        return;
    }

    setTimeout(() => playTTSById(messageId), 500);
}

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

    const messageId = `msg_${Date.now()}`;
    addMessage('user', message, messageId);

    input.value = '';
    input.style.height = 'auto';

    AppState.messageCount++;

    if (AppState.messageCount === 3) showLinkedInCTA();

    sendBtn.disabled = true;
    sendBtnText.innerHTML = '<span class="spinner"></span>';

    updateStatus('thinking', 'Generating response...');

    const skeletonId = `skeleton_${Date.now()}`;
    showSkeletonLoader(skeletonId);

    try {
        const response = await fetch(`${API_BASE}/assistant/api/chat/`, {
            method: 'POST',
            headers: getAPIHeaders(),
            body: JSON.stringify({
                session_id: AppState.sessionId,
                message: message
            })
        });

        removeSkeletonLoader(skeletonId);

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();

        if (data.reply) {
            const cleanReply = stripMarkdown(data.reply);
            const aiMessageId = `msg_${Date.now()}`;
            addMessage('assistant', cleanReply, aiMessageId);

            autoPlayTTSForMessage(aiMessageId);

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

async function retryMessage(originalMessage, messageElement) {
    const retryBtn = messageElement.querySelector('.btn-retry');
    if (retryBtn) {
        retryBtn.disabled = true;
        retryBtn.innerHTML = '<span class="spinner"></span> Retrying...';
    }

    updateStatus('thinking', 'Retrying...');

    const skeletonId = `skeleton_${Date.now()}`;
    showSkeletonLoader(skeletonId);

    try {
        const response = await fetch(`${API_BASE}/assistant/api/chat/`, {
            method: 'POST',
            headers: getAPIHeaders(),
            body: JSON.stringify({
                session_id: AppState.sessionId,
                message: originalMessage
            })
        });

        removeSkeletonLoader(skeletonId);

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();

        if (data.reply) {
            messageElement.remove();

            const cleanReply = stripMarkdown(data.reply);
            const aiMessageId = `msg_${Date.now()}`;
            addMessage('assistant', cleanReply, aiMessageId);

            autoPlayTTSForMessage(aiMessageId);

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

function removeSkeletonLoader(skeletonId) {
    const skeleton = document.getElementById(skeletonId);
    if (skeleton) skeleton.remove();
}

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

    const plainText = content.replace(/<[^>]*>/g, '');

    if (role === 'assistant') MESSAGE_TEXTS.set(messageId, plainText);

    let messageHTML = `
        <div class="message-bubble">
            <div class="message-content">${content}</div>
            <div class="message-footer">
                <span class="message-timestamp">${timestamp}</span>
                <div class="message-actions">
    `;

    messageHTML += `
                    <button class="btn-icon" 
                            onclick="copyToClipboard('${escapeForJs(plainText)}')"
                            title="Copy message"
                            aria-label="Copy message">
                        <i class="bi bi-clipboard"></i>
                    </button>
    `;

    if (role === 'assistant' && AppState.voiceEnabled) {
        messageHTML += `
                    <button class="btn-icon" 
                            onclick="playTTSById('${messageId}')"
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
    if (indicator) indicator.remove();
}

function handleQuickAction(text) {
    const input = document.getElementById('userInput');
    if (input) {
        input.value = text;
        sendMessage();
        trackEvent('quick_action_used', { text });
    }
}

async function startChat() {
    if (!AppState.sessionId) initSession();

    updateStatus('thinking', 'Connecting...');

    const skeletonId = `skeleton_${Date.now()}`;
    showSkeletonLoader(skeletonId);

    try {
        const response = await fetch(`${API_BASE}/assistant/api/chat/`, {
            method: 'POST',
            headers: getAPIHeaders(),
            body: JSON.stringify({
                session_id: AppState.sessionId,
                message: 'Hello'
            })
        });

        removeSkeletonLoader(skeletonId);

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();

        if (data.reply) {
            const cleanReply = stripMarkdown(data.reply);
            const messageId = `msg_${Date.now()}`;
            addMessage('assistant', cleanReply, messageId);

            autoPlayTTSForMessage(messageId);

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
    if (linkedinCta) linkedinCta.style.display = 'none';

    if (typeof stopTTS === 'function') stopTTS();

    MESSAGE_TEXTS.clear();

    initSession();
    await startChat();

    showToast('New conversation started', 'success', 2000);
    trackEvent('chat_reset');
}

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

function showLinkedInCTA() {
    const cta = document.getElementById('linkedinCta');
    if (cta && cta.style.display !== 'block') {
        cta.style.display = 'block';
        cta.style.animation = 'messageSlideIn 0.4s ease-out';
        trackEvent('linkedin_cta_shown');
    }
}

function setupChatListeners() {
    const input = document.getElementById('userInput');
    const sendBtn = document.getElementById('sendBtn');

    if (input) {
        input.addEventListener('keypress', handleInputKeypress);
        input.addEventListener('input', (e) => autoResizeTextarea(e.target));
    }

    if (sendBtn) sendBtn.addEventListener('click', sendMessage);
}

document.addEventListener('DOMContentLoaded', () => {
    if (!document.getElementById('chatMessages')) return;

    console.log('[Chat] Initializing...');
    setupChatListeners();
    setTimeout(startChat, 500);
});