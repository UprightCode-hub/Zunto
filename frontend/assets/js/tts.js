/**
 * GigiAI - Text-to-Speech Module
 * API: POST ${API_BASE}/assistant/api/tts/
 */

// ============================================
// TTS PLAYBACK
// ============================================

/**
 * Play text-to-speech
 * @param {HTMLElement} button - Play button
 * @param {string} text - Text to speak
 * @param {string} messageId - Message ID for tracking
 */
async function playTTS(button, text, messageId = null) {
    // Stop any currently playing audio
    if (AppState.currentAudio) {
        stopTTS();
    }
    
    // If clicking same button that's playing, just stop
    if (button.classList.contains('playing')) {
        stopTTS();
        return;
    }
    
    try {
        button.classList.add('playing');
        button.innerHTML = '<i class="bi bi-hourglass-split"></i>';
        button.setAttribute('aria-label', 'Loading audio...');
        
        // API call - DO NOT MODIFY ENDPOINT
        const response = await fetch(`${API_BASE}/assistant/api/tts/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: text,
                voice: 'alloy',
                speed: 1.0,
                use_cache: true
            })
        });
        
        if (!response.ok) {
            throw new Error(`TTS API error: ${response.status}`);
        }
        
        // Get audio blob
        const audioBlob = await response.blob();
        const audioUrl = URL.createObjectURL(audioBlob);
        
        // Create audio
        AppState.currentAudio = new Audio(audioUrl);
        
        // Update button
        button.innerHTML = '<i class="bi bi-pause-fill"></i>';
        button.setAttribute('aria-label', 'Pause audio');
        
        // Handle audio end
        AppState.currentAudio.onended = () => {
            resetTTSButton(button);
            AppState.currentAudio = null;
            URL.revokeObjectURL(audioUrl);
            if (typeof trackEvent === 'function') {
                trackEvent('tts_completed', { messageId });
            }
        };
        
        // Handle audio error
        AppState.currentAudio.onerror = () => {
            resetTTSButton(button);
            AppState.currentAudio = null;
            URL.revokeObjectURL(audioUrl);
            if (typeof showToast === 'function') {
                showToast('Audio playback failed', 'error');
            }
            if (typeof trackEvent === 'function') {
                trackEvent('tts_error', { messageId });
            }
        };
        
        // Start playback
        await AppState.currentAudio.play();
        if (typeof trackEvent === 'function') {
            trackEvent('tts_played', { messageId, textLength: text.length });
        }
        
    } catch (error) {
        console.error('[TTS] Error:', error);
        resetTTSButton(button);
        
        // Degrade gracefully
        if (typeof showToast === 'function') {
            showToast('Voice unavailable right now', 'error', 2000);
        }
        if (typeof trackEvent === 'function') {
            trackEvent('tts_failed', { error: error.message });
        }
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
    document.querySelectorAll('.btn-icon.playing').forEach(btn => {
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
// VOICE TOGGLE
// ============================================

/**
 * Toggle voice on/off globally
 */
function toggleVoice() {
    AppState.voiceEnabled = !AppState.voiceEnabled;
    
    const voiceBtn = document.getElementById('voiceToggle');
    if (voiceBtn) {
        const icon = voiceBtn.querySelector('i');
        const text = voiceBtn.querySelector('span');
        
        if (AppState.voiceEnabled) {
            icon.className = 'bi bi-volume-up-fill';
            if (text) text.textContent = 'Voice';
            voiceBtn.setAttribute('aria-label', 'Voice enabled. Click to disable');
        } else {
            icon.className = 'bi bi-volume-mute-fill';
            if (text) text.textContent = 'Muted';
            voiceBtn.setAttribute('aria-label', 'Voice disabled. Click to enable');
        }
    }
    
    // Stop any playing audio when disabling
    if (!AppState.voiceEnabled) {
        stopTTS();
    }
    
    // Save preference
    if (typeof saveToStorage === 'function') {
        saveToStorage('voiceEnabled', AppState.voiceEnabled);
    }
    
    // Show feedback
    if (typeof showToast === 'function') {
        showToast(
            AppState.voiceEnabled ? 'Voice enabled' : 'Voice disabled',
            'info',
            2000
        );
    }
    
    if (typeof trackEvent === 'function') {
        trackEvent('voice_toggle', { enabled: AppState.voiceEnabled });
    }
}

// ============================================
// INITIALIZATION
// ============================================

function initTTS() {
    // Load voice preference
    if (typeof loadFromStorage === 'function') {
        const savedVoiceEnabled = loadFromStorage('voiceEnabled', true);
        AppState.voiceEnabled = savedVoiceEnabled;
    }
    
    // Update UI if button exists
    const voiceBtn = document.getElementById('voiceToggle');
    if (voiceBtn) {
        const icon = voiceBtn.querySelector('i');
        const text = voiceBtn.querySelector('span');
        
        if (AppState.voiceEnabled) {
            icon.className = 'bi bi-volume-up-fill';
            if (text) text.textContent = 'Voice';
        } else {
            icon.className = 'bi bi-volume-mute-fill';
            if (text) text.textContent = 'Muted';
        }
    }
    
    console.log('[TTS] Initialized. Voice enabled:', AppState.voiceEnabled);
}

// ============================================
// CLEANUP
// ============================================

window.addEventListener('beforeunload', () => {
    stopTTS();
});

document.addEventListener('visibilitychange', () => {
    if (document.hidden && AppState.currentAudio) {
        stopTTS();
    }
});

// Auto-initialize
document.addEventListener('DOMContentLoaded', initTTS);
