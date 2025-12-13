/**
 * GigiAI - Chat Module (UPGRADED)
 * Handles messaging, skeleton loaders, retry, copy, and TTS
 * API: POST ${API_BASE}/assistant/api/chat/
 * 
 * FIXES:
 * - TTS button works with long/formatted text (data attributes)
 * - Frontend audio caching (no regeneration on replay)
 * - Auto-play TTS for assistant responses (optional)
 */

// ============================================
// AUDIO CACHE
// ============================================

/**
 * Frontend audio cache to prevent regenerating TTS
 * Key: messageId -> Value: { audioUrl, text }
 */
const AUDIO_CACHE = new Map();

/**
 * Maximum cached audio files (prevent memory leaks)
 */
const MAX_AUDIO_CACHE_SIZE = 50;

/**
 * Clear old cached audio when limit is reached
 */
function cleanAudioCache() {
    if (AUDIO_CACHE.size > MAX_AUDIO_CACHE_SIZE) {
        // Remove oldest 10 entries
        const keysToDelete = Array.from(AUDIO_CACHE.keys()).slice(0, 10);
        keysToDelete.forEach(key => {
            const cached = AUDIO_CACHE.get(key);
            if (cached && cached.audioUrl) {
                URL.revokeObjectURL(cached.audioUrl);
            }
            AUDIO_CACHE.delete(key);
        });
        console.log('[AudioCache] Cleaned', keysToDelete.length, 'entries');
    }
}

/**
 * Get cached audio for a message
 */
function getCachedAudio(messageId) {
    return AUDIO_CACHE.get(messageId);
}

/**
 * Cache audio for a message
 */
function setCachedAudio(messageId, audioUrl, text) {
    cleanAudioCache();
    AUDIO_CACHE.set(messageId, { audioUrl, text });
}

/**
 * Clear all cached audio (called on reset/cleanup)
 */
function clearAllAudioCache() {
    AUDIO_CACHE.forEach((cached) => {
        if (cached.audioUrl) {
            URL.revokeObjectURL(cached.audioUrl);
        }
    });
    AUDIO_CACHE.clear();
    console.log('[AudioCache] Cleared all cached audio');
}

// ============================================
// MESSAGE MANAGEMENT
// ============================================

/**
 * Send message to AI
 * CRITICAL: Adds skeleton, handles retry, auto-plays TTS
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
            const plainText = cleanReply.replace(/<[^>]*>/g, ''); // Extract plain text for TTS
            const aiMessageId = `msg_${Date.now()}`;
            
            // Add message to UI
            addMessage('assistant', cleanReply, aiMessageId, plainText);
            
            // âœ… AUTO-PLAY TTS (optional - comment out if you don't want auto-play)
            if (AppState.voiceEnabled) {
                setTimeout(() => {
                    autoPlayTTS(aiMessageId, plainText);
                }, 500);
            }
            
            updateStatus('connected', 'Connected');
            trackEvent('message_received', { length: data.reply.length });
        } else if (data.error) {
            addMessage('assistant', 'Sorry, I encountered an error processing your message.', `msg_${Date.now()}`);
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
            const plainText = cleanReply.replace(/<[^>]*>/g, '');
            const aiMessageId = `msg_${Date.now()}`;
            addMessage('assistant', cleanReply, aiMessageId, plainText);
            
            // Auto-play TTS
            if (AppState.voiceEnabled) {
                setTimeout(() => {
                    autoPlayTTS(aiMessageId, plainText);
                }, 500);
            }
            
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
 * @param {string} plainText - Plain text for TTS (optional, extracted if not provided)
 */
function addMessage(role, content, messageId, plainText = null) {
    const container = document.getElementById('chatMessages');
    if (!container) return;
    
    const messagesList = container.querySelector('.messages-list') || container;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    messageDiv.id = messageId;
    messageDiv.setAttribute('role', 'article');
    messageDiv.setAttribute('aria-label', `${role === 'user' ? 'Your' : 'Assistant'} message`);
    
    const timestamp = formatTime();
    
    // Extract plain text if not provided
    if (!plainText) {
        plainText = content.replace(/<[^>]*>/g, '');
    }
    
    let messageHTML = `
        <div class="message-bubble">
            <div class="message-content">${content}</div>
            <div class="message-footer">
                <span class="message-timestamp">${timestamp}</span>
                <div class="message-actions">
    `;
    
    // Copy button for all messages
    messageHTML += `
                    <button class="btn-icon btn-copy" 
                            data-text="${escapeForJs(plainText)}"
                            title="Copy message"
                            aria-label="Copy message">
                        <i class="bi bi-clipboard"></i>
                    </button>
    `;
    
    // âœ… TTS button for assistant messages (FIXED with data attributes)
    if (role === 'assistant' && AppState.voiceEnabled) {
        messageHTML += `
                    <button class="btn-icon btn-tts" 
                            data-message-id="${messageId}"
                            data-text="${escapeForJs(plainText)}"
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
// TTS FUNCTIONS
// ============================================

/**
 * Auto-play TTS for assistant messages
 * @param {string} messageId - Message ID
 * @param {string} text - Text to speak
 */
async function autoPlayTTS(messageId, text) {
    if (!AppState.voiceEnabled) return;
    
    const messageEl = document.getElementById(messageId);
    if (!messageEl) return;
    
    const ttsButton = messageEl.querySelector('.btn-tts');
    if (!ttsButton) return;
    
    // Small delay to ensure DOM is ready
    await new Promise(resolve => setTimeout(resolve, 100));
    
    // Trigger playback
    playTTSForMessage(ttsButton, messageId, text);
}

/**
 * Play TTS with caching support
 * @param {HTMLElement} button - TTS button element
 * @param {string} messageId - Message ID for caching
 * @param {string} text - Text to speak
 */
async function playTTSForMessage(button, messageId, text) {
    // Stop any currently playing audio
    if (AppState.currentAudio) {
        stopTTS();
    }
    
    // If clicking same button that's playing, just stop
    if (button.classList.contains('playing')) {
        stopTTS();
        return;
    }
    
    // Check if we have cached audio
    const cached = getCachedAudio(messageId);
    if (cached && cached.audioUrl) {
        console.log('[TTS] Using cached audio for message', messageId);
        playAudioFromUrl(button, cached.audioUrl, messageId);
        return;
    }
    
    // No cache - fetch from API
    try {
        button.classList.add('playing');
        button.innerHTML = '<i class="bi bi-hourglass-split"></i>';
        button.setAttribute('aria-label', 'Loading audio...');
        
        // API call - with caching enabled
        const response = await fetch(`${API_BASE}/assistant/api/tts/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: text,
                voice: 'alloy',
                speed: 1.0,
                use_cache: true  // Backend caching
            })
        });
        
        if (!response.ok) {
            throw new Error(`TTS API error: ${response.status}`);
        }
        
        // Get audio blob
        const audioBlob = await response.blob();
        const audioUrl = URL.createObjectURL(audioBlob);
        
        // âœ… Cache the audio URL
        setCachedAudio(messageId, audioUrl, text);
        
        // Play the audio
        playAudioFromUrl(button, audioUrl, messageId);
        
    } catch (error) {
        console.error('[TTS] Error:', error);
        resetTTSButton(button);
        
        if (typeof showToast === 'function') {
            showToast('Voice unavailable right now', 'error', 2000);
        }
        if (typeof trackEvent === 'function') {
            trackEvent('tts_failed', { error: error.message });
        }
    }
}

/**
 * Play audio from cached or fresh URL
 * @param {HTMLElement} button - TTS button
 * @param {string} audioUrl - Blob URL
 * @param {string} messageId - Message ID
 */
function playAudioFromUrl(button, audioUrl, messageId) {
    // Create audio element
    AppState.currentAudio = new Audio(audioUrl);
    
    // Update button
    button.classList.add('playing');
    button.innerHTML = '<i class="bi bi-pause-fill"></i>';
    button.setAttribute('aria-label', 'Pause audio');
    
    // Handle audio end
    AppState.currentAudio.onended = () => {
        resetTTSButton(button);
        AppState.currentAudio = null;
        
        if (typeof trackEvent === 'function') {
            trackEvent('tts_completed', { messageId });
        }
    };
    
    // Handle audio error
    AppState.currentAudio.onerror = () => {
        resetTTSButton(button);
        AppState.currentAudio = null;
        
        if (typeof showToast === 'function') {
            showToast('Audio playback failed', 'error');
        }
        if (typeof trackEvent === 'function') {
            trackEvent('tts_error', { messageId });
        }
    };
    
    // Start playback
    AppState.currentAudio.play().catch(err => {
        console.error('[TTS] Playback error:', err);
        resetTTSButton(button);
        AppState.currentAudio = null;
    });
    
    if (typeof trackEvent === 'function') {
        trackEvent('tts_played', { messageId, cached: true });
    }
}

/**
 * Stop currently playing TTS
 */
function stopTTS() {
    if (AppState.currentAudio) {
        AppState.currentAudio.pause();
        AppState.currentAudio = null;
    }
    
    // Reset all TTS buttons
    document.querySelectorAll('.btn-tts.playing').forEach(btn => {
        resetTTSButton(btn);
    });
}

/**
 * Reset TTS button to default state
 * @param {HTMLElement} button - Button element
 */
function resetTTSButton(button) {
    button.classList.remove('playing');
    button.innerHTML = '<i class="bi bi-play-fill"></i>';
    button.setAttribute('aria-label', 'Play audio');
}

// ============================================
// EVENT DELEGATION FOR BUTTONS
// ============================================

/**
 * Handle TTS button clicks via event delegation
 * Fixes bug where inline onclick breaks with long/formatted text
 */
document.addEventListener('click', (e) => {
    // TTS button
    const ttsButton = e.target.closest('.btn-tts');
    if (ttsButton) {
        const messageId = ttsButton.getAttribute('data-message-id');
        const text = ttsButton.getAttribute('data-text');
        
        if (text) {
            playTTSForMessage(ttsButton, messageId, text);
        }
        return;
    }
    
    // Copy button
    const copyButton = e.target.closest('.btn-copy');
    if (copyButton) {
        const text = copyButton.getAttribute('data-text');
        if (text && typeof copyToClipboard === 'function') {
            copyToClipboard(text);
        }
        return;
    }
});

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
            const plainText = cleanReply.replace(/<[^>]*>/g, '');
            const messageId = `msg_${Date.now()}`;
            addMessage('assistant', cleanReply, messageId, plainText);
            
            // Auto-play first message
            if (AppState.voiceEnabled) {
                setTimeout(() => {
                    autoPlayTTS(messageId, plainText);
                }, 500);
            }
            
            updateStatus('connected', 'Connected');
            AppState.isConnected = true;
            trackEvent('chat_started');
        } else if (data.error) {
            addMessage('assistant', 'Sorry, I encountered an error. Please type your name and press Enter to continue.', `msg_${Date.now()}`);
            updateStatus('error', 'Connection error');
            showToast('Connection hiccup â€” type your name to continue', 'warning', 5000);
        }
        
    } catch (error) {
        console.error('[Chat] Start error:', error);
        removeSkeletonLoader(skeletonId);
        addMessage('assistant', 'Connection failed. Please type your name and press Enter to retry.', `msg_${Date.now()}`);
        updateStatus('error', 'Connection failed');
        showToast('Failed to connect â€” type your name to continue', 'error', 5000);
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
    
    // Stop any playing audio
    stopTTS();
    
    // Clear audio cache
    clearAllAudioCache();
    
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
// CLEANUP
// ============================================

window.addEventListener('beforeunload', () => {
    stopTTS();
    clearAllAudioCache();
});

document.addEventListener('visibilitychange', () => {
    if (document.hidden && AppState.currentAudio) {
        stopTTS();
    }
});

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    if (!document.getElementById('chatMessages')) return;
    
    console.log('[Chat] Initializing...');
    setupChatListeners();
    setTimeout(startChat, 500);
});
