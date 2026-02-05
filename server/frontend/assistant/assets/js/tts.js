const TTS_DEFAULTS = {
    voice: 'alloy',
    speed: 1.0,
    autoPlay: false,
    enabled: true
};

const AVAILABLE_VOICES = {
    'alloy': { name: 'Alloy', description: 'Neutral & balanced', gender: 'neutral' },
    'echo': { name: 'Echo', description: 'Male, clear', gender: 'male' },
    'fable': { name: 'Fable', description: 'Female, expressive', gender: 'female' },
    'onyx': { name: 'Onyx', description: 'Male, deep & warm', gender: 'male' },
    'nova': { name: 'Nova', description: 'Female, friendly', gender: 'female' },
    'shimmer': { name: 'Shimmer', description: 'Female, bright', gender: 'female' }
};

function getTTSSettings() {
    if (typeof loadFromStorage === 'function') {
        return {
            voice: loadFromStorage('tts_voice', TTS_DEFAULTS.voice),
            speed: parseFloat(loadFromStorage('tts_speed', TTS_DEFAULTS.speed)),
            autoPlay: loadFromStorage('tts_autoPlay', TTS_DEFAULTS.autoPlay),
            enabled: loadFromStorage('voiceEnabled', TTS_DEFAULTS.enabled)
        };
    }
    return { ...TTS_DEFAULTS };
}

function saveTTSSettings(settings) {
    if (typeof saveToStorage === 'function') {
        saveToStorage('tts_voice', settings.voice);
        saveToStorage('tts_speed', settings.speed);
        saveToStorage('tts_autoPlay', settings.autoPlay);
        saveToStorage('voiceEnabled', settings.enabled);
    }
}

async function playTTS(button, text, messageId = null) {
    if (AppState.currentAudio) stopTTS();

    if (button.classList.contains('playing')) {
        stopTTS();
        return;
    }

    try {
        button.classList.add('playing');
        button.innerHTML = '<i class="bi bi-hourglass-split"></i>';
        button.setAttribute('aria-label', 'Loading audio...');

        const settings = getTTSSettings();

        const response = await fetch(`${API_BASE}/assistant/api/tts/`, {
            method: 'POST',
            headers: getAPIHeaders(),
            body: JSON.stringify({
                text: text,
                voice: settings.voice,
                speed: settings.speed,
                use_cache: true
            })
        });

        if (!response.ok) throw new Error(`TTS API error: ${response.status}`);

        const audioBlob = await response.blob();
        const audioUrl = URL.createObjectURL(audioBlob);

        AppState.currentAudio = new Audio(audioUrl);

        button.innerHTML = '<i class="bi bi-pause-fill"></i>';
        button.setAttribute('aria-label', 'Pause audio');

        AppState.currentAudio.onended = () => {
            resetTTSButton(button);
            AppState.currentAudio = null;
            URL.revokeObjectURL(audioUrl);
            if (typeof trackEvent === 'function') {
                trackEvent('tts_completed', { messageId, voice: settings.voice, speed: settings.speed });
            }
        };

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

        await AppState.currentAudio.play();
        if (typeof trackEvent === 'function') {
            trackEvent('tts_played', { 
                messageId, 
                textLength: text.length,
                voice: settings.voice,
                speed: settings.speed
            });
        }

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

function stopTTS() {
    if (AppState.currentAudio) {
        AppState.currentAudio.pause();
        AppState.currentAudio = null;
    }

    document.querySelectorAll('.btn-icon.playing').forEach(btn => resetTTSButton(btn));
}

function resetTTSButton(button) {
    button.classList.remove('playing');
    button.innerHTML = '<i class="bi bi-play-fill"></i>';
    button.setAttribute('aria-label', 'Play audio');
}

function toggleVoice() {
    const settings = getTTSSettings();
    settings.enabled = !settings.enabled;
    AppState.voiceEnabled = settings.enabled;
    saveTTSSettings(settings);

    const voiceBtn = document.getElementById('voiceToggle');
    if (voiceBtn) {
        const icon = voiceBtn.querySelector('i');
        const text = voiceBtn.querySelector('span');

        if (settings.enabled) {
            icon.className = 'bi bi-volume-up-fill';
            if (text) text.textContent = 'Voice';
            voiceBtn.setAttribute('aria-label', 'Voice enabled. Click to disable');
        } else {
            icon.className = 'bi bi-volume-mute-fill';
            if (text) text.textContent = 'Muted';
            voiceBtn.setAttribute('aria-label', 'Voice disabled. Click to enable');
        }
    }

    if (!settings.enabled) stopTTS();

    if (typeof showToast === 'function') {
        showToast(settings.enabled ? 'Voice enabled' : 'Voice disabled', 'info', 2000);
    }

    if (typeof trackEvent === 'function') {
        trackEvent('voice_toggle', { enabled: settings.enabled });
    }
}

function showVoiceSettings() {
    if (!document.getElementById('voiceSettingsModal')) createVoiceSettingsModal();

    const settings = getTTSSettings();

    const voiceSelect = document.getElementById('voiceSelect');
    const speedSlider = document.getElementById('speedSlider');
    const speedValue = document.getElementById('speedValue');
    const autoPlayToggle = document.getElementById('autoPlayToggle');

    if (voiceSelect) voiceSelect.value = settings.voice;
    if (speedSlider) {
        speedSlider.value = settings.speed;
        if (speedValue) speedValue.textContent = `${settings.speed}x`;
    }
    if (autoPlayToggle) autoPlayToggle.checked = settings.autoPlay;

    const modal = document.getElementById('voiceSettingsModal');
    if (modal) modal.classList.add('visible');

    if (typeof trackEvent === 'function') trackEvent('voice_settings_opened');
}

function hideVoiceSettings() {
    const modal = document.getElementById('voiceSettingsModal');
    if (modal) modal.classList.remove('visible');
}

function createVoiceSettingsModal() {
    const settings = getTTSSettings();

    const voiceOptionsHTML = Object.entries(AVAILABLE_VOICES).map(([key, voice]) => `
        <option value="${key}" ${settings.voice === key ? 'selected' : ''}>
            ${voice.name} — ${voice.description}
        </option>
    `).join('');

    const html = `
        <div class="modal-overlay" id="voiceSettingsModal">
            <div class="modal-content voice-settings-modal">
                <div class="modal-header">
                    <h2>
                        <i class="bi bi-sliders"></i>
                        Voice Settings
                    </h2>
                    <button class="btn-close" onclick="hideVoiceSettings()" aria-label="Close settings">
                        <i class="bi bi-x-lg"></i>
                    </button>
                </div>
                
                <div class="modal-body">
                    <div class="settings-group">
                        <label for="voiceSelect">
                            <i class="bi bi-person-bounding-box"></i>
                            Voice Style
                        </label>
                        <select id="voiceSelect" class="settings-select" onchange="updateVoice(this.value)">
                            ${voiceOptionsHTML}
                        </select>
                        <small class="settings-hint">Choose a voice that suits your preference</small>
                    </div>
                    
                    <div class="settings-group">
                        <label for="speedSlider">
                            <i class="bi bi-speedometer2"></i>
                            Speech Speed: <span id="speedValue">${settings.speed}x</span>
                        </label>
                        <input type="range" 
                               id="speedSlider" 
                               class="settings-slider" 
                               min="0.5" 
                               max="2.0" 
                               step="0.1" 
                               value="${settings.speed}"
                               oninput="updateSpeed(this.value)">
                        <div class="slider-labels">
                            <span>0.5x (Slower)</span>
                            <span>2.0x (Faster)</span>
                        </div>
                    </div>
                    
                    <div class="settings-group">
                        <label class="settings-toggle">
                            <input type="checkbox" 
                                   id="autoPlayToggle"
                                   ${settings.autoPlay ? 'checked' : ''}
                                   onchange="updateAutoPlay(this.checked)">
                            <span class="toggle-slider"></span>
                            <span class="toggle-label">
                                <i class="bi bi-play-circle"></i>
                                Auto-play responses
                            </span>
                        </label>
                        <small class="settings-hint">Automatically play audio for assistant messages</small>
                    </div>
                    
                    <button class="btn btn-secondary" onclick="testVoice()" style="width: 100%; margin-top: 1rem;">
                        <i class="bi bi-megaphone"></i>
                        Test Voice
                    </button>
                </div>
                
                <div class="modal-footer">
                    <button class="btn btn-ghost" onclick="resetVoiceSettings()">
                        <i class="bi bi-arrow-counterclockwise"></i>
                        Reset to Default
                    </button>
                    <button class="btn btn-primary" onclick="hideVoiceSettings()">
                        Done
                    </button>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', html);

    const modal = document.getElementById('voiceSettingsModal');
    modal.addEventListener('click', (e) => {
        if (e.target === modal) hideVoiceSettings();
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.classList.contains('visible')) hideVoiceSettings();
    });
}

function updateVoice(voice) {
    const settings = getTTSSettings();
    settings.voice = voice;
    saveTTSSettings(settings);

    if (typeof trackEvent === 'function') trackEvent('voice_changed', { voice });
}

function updateSpeed(speed) {
    const settings = getTTSSettings();
    settings.speed = parseFloat(speed);
    saveTTSSettings(settings);

    const speedValue = document.getElementById('speedValue');
    if (speedValue) speedValue.textContent = `${speed}x`;

    if (typeof trackEvent === 'function') trackEvent('speed_changed', { speed });
}

function updateAutoPlay(enabled) {
    const settings = getTTSSettings();
    settings.autoPlay = enabled;
    saveTTSSettings(settings);

    if (typeof showToast === 'function') {
        showToast(enabled ? 'Auto-play enabled' : 'Auto-play disabled', 'info', 2000);
    }

    if (typeof trackEvent === 'function') trackEvent('autoplay_changed', { enabled });
}

function resetVoiceSettings() {
    const confirmed = confirm('Reset voice settings to default?');
    if (!confirmed) return;

    saveTTSSettings(TTS_DEFAULTS);

    const voiceSelect = document.getElementById('voiceSelect');
    const speedSlider = document.getElementById('speedSlider');
    const speedValue = document.getElementById('speedValue');
    const autoPlayToggle = document.getElementById('autoPlayToggle');

    if (voiceSelect) voiceSelect.value = TTS_DEFAULTS.voice;
    if (speedSlider) speedSlider.value = TTS_DEFAULTS.speed;
    if (speedValue) speedValue.textContent = `${TTS_DEFAULTS.speed}x`;
    if (autoPlayToggle) autoPlayToggle.checked = TTS_DEFAULTS.autoPlay;

    if (typeof showToast === 'function') showToast('Settings reset to default', 'success', 2000);

    if (typeof trackEvent === 'function') trackEvent('voice_settings_reset');
}

async function testVoice() {
    const settings = getTTSSettings();
    const voiceInfo = AVAILABLE_VOICES[settings.voice];

    const testText = `Hello! I'm ${voiceInfo.name}. This is how I sound at ${settings.speed}x speed.`;

    const testBtn = document.createElement('button');
    testBtn.style.display = 'none';
    document.body.appendChild(testBtn);

    try {
        await playTTS(testBtn, testText, 'test');
    } finally {
        setTimeout(() => testBtn.remove(), 1000);
    }

    if (typeof trackEvent === 'function') {
        trackEvent('voice_tested', { voice: settings.voice, speed: settings.speed });
    }
}

function initTTS() {
    const settings = getTTSSettings();
    AppState.voiceEnabled = settings.enabled;

    const voiceBtn = document.getElementById('voiceToggle');
    if (voiceBtn) {
        const icon = voiceBtn.querySelector('i');
        const text = voiceBtn.querySelector('span');

        if (settings.enabled) {
            icon.className = 'bi bi-volume-up-fill';
            if (text) text.textContent = 'Voice';
        } else {
            icon.className = 'bi bi-volume-mute-fill';
            if (text) text.textContent = 'Muted';
        }
    }

    console.log('[TTS] Init', settings.voice, settings.speed);
}

window.addEventListener('beforeunload', () => stopTTS());

document.addEventListener('visibilitychange', () => {
    if (document.hidden && AppState.currentAudio) stopTTS();
});

document.addEventListener('DOMContentLoaded', initTTS);