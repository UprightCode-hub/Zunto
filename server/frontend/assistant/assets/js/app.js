const API_BASE = '';

const APP_CONFIG = {
    version: '2.2.0',
    maxMessageLength: 1000,
    typingDelay: 500,
    toastDuration: 3000,
    autoScrollDelay: 100,
    retryMaxAttempts: 3
};

const AppState = {
    sessionId: null,
    currentAudio: null,
    voiceEnabled: true,
    messageCount: 0,
    isConnected: false,
    isTyping: false,
    currentStatus: 'disconnected',
    pendingRetries: new Map(),
    currentTheme: 'system'
};

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function getCSRFToken() {
    let token = getCookie('csrftoken');
    if (!token) {
        const metaToken = document.querySelector('meta[name="csrf-token"]');
        if (metaToken) token = metaToken.getAttribute('content');
    }
    if (!token) {
        const inputToken = document.querySelector('input[name="csrfmiddlewaretoken"]');
        if (inputToken) token = inputToken.value;
    }
    return token;
}

function getAPIHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    const csrfToken = getCSRFToken();
    if (csrfToken) headers['X-CSRFToken'] = csrfToken;
    return headers;
}

function initTheme() {
    const savedTheme = loadFromStorage('theme', 'system');
    AppState.currentTheme = savedTheme;
    applyTheme(savedTheme);

    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        if (AppState.currentTheme === 'system') applySystemTheme();
    });
}

function applyTheme(theme) {
    AppState.currentTheme = theme;
    saveToStorage('theme', theme);

    if (theme === 'system') {
        applySystemTheme();
    } else {
        document.documentElement.setAttribute('data-theme', theme);
    }
    updateThemeIcon(theme);
}

function applySystemTheme() {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    document.documentElement.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
}

function toggleTheme() {
    const themes = ['light', 'dark', 'system'];
    const currentIndex = themes.indexOf(AppState.currentTheme);
    const nextTheme = themes[(currentIndex + 1) % themes.length];

    applyTheme(nextTheme);

    const themeNames = { light: 'Light mode', dark: 'Dark mode', system: 'System mode' };
    showToast(`${themeNames[nextTheme]} activated`, 'info', 2000);
    trackEvent('theme_changed', { theme: nextTheme });
}

function updateThemeIcon(theme) {
    const themeBtn = document.querySelector('[onclick*="toggleTheme"]');
    if (!themeBtn) return;

    const icon = themeBtn.querySelector('i');
    const text = themeBtn.querySelector('.theme-text');

    const themeIcons = { light: 'bi-sun-fill', dark: 'bi-moon-fill', system: 'bi-circle-half' };
    const themeLabels = { light: 'Light Mode', dark: 'Dark Mode', system: 'System Mode' };

    if (icon) icon.className = `bi ${themeIcons[theme]}`;
    if (text) text.textContent = themeLabels[theme];
}

function updateStatus(status, message = '') {
    AppState.currentStatus = status;

    const statusBar = document.getElementById('statusBar');
    const statusDot = document.getElementById('statusDot');
    const statusText = document.getElementById('statusText');

    if (!statusBar || !statusDot || !statusText) return;

    statusDot.className = 'status-dot';
    statusDot.classList.add(status);

    const statusMessages = {
        connected: message || 'Connected',
        thinking: message || 'Thinking...',
        error: message || 'Connection error',
        disconnected: message || 'Disconnected'
    };

    statusText.textContent = statusMessages[status] || message;

    if (status === 'connected') {
        setTimeout(() => statusBar.classList.add('hidden'), 2000);
    } else {
        statusBar.classList.remove('hidden');
    }

    const glowWrapper = document.querySelector('.input-glow-wrapper');
    if (glowWrapper) {
        if (status === 'thinking') {
            glowWrapper.classList.add('ai-generating');
        } else {
            glowWrapper.classList.remove('ai-generating');
        }
    }
}

function generateSessionId() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

function initSession() {
    AppState.sessionId = generateSessionId();
    console.log(`[Session] ${AppState.sessionId}`);
    return AppState.sessionId;
}

function trackEvent(eventName, data = {}) {
    console.log('[Analytics]', eventName, data);
    if (typeof gtag !== 'undefined') gtag('event', eventName, data);
}

function showToast(message, type = 'info', duration = APP_CONFIG.toastDuration) {
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toastMessage');

    if (!toast || !toastMessage) return;

    toastMessage.textContent = message;
    toast.className = `toast ${type}`;
    toast.classList.add('visible');

    setTimeout(() => toast.classList.remove('visible'), duration);
}

function toggleDropdown(menuId) {
    const menu = document.getElementById(menuId);
    if (!menu) return;

    document.querySelectorAll('.dropdown-menu').forEach(m => {
        if (m.id !== menuId) m.classList.remove('visible');
    });

    menu.classList.toggle('visible');
    trackEvent('dropdown_toggle', { menuId });
}

function closeAllDropdowns() {
    document.querySelectorAll('.dropdown-menu').forEach(menu => menu.classList.remove('visible'));
}

document.addEventListener('click', (e) => {
    if (!e.target.closest('.dropdown')) closeAllDropdowns();
});

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeAllDropdowns();
});

function stripMarkdown(text) {
    if (!text) return '';

    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    text = text.replace(/__(.*?)__/g, '<strong>$1</strong>');
    text = text.replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>');
    text = text.replace(/(?<!_)_(?!_)(.+?)(?<!_)_(?!_)/g, '<em>$1</em>');
    text = text.replace(/^#{1,6}\s+(.+)$/gm, '<strong>$1</strong>');
    text = text.replace(/```[\s\S]*?```/g, '');
    text = text.replace(/`(.+?)`/g, '<code>$1</code>');
    text = text.replace(/^[-*_]{3,}$/gm, '');
    text = text.replace(/\[([^\]]+)\]\([^\)]+\)/g, '$1');
    text = text.replace(/!\[([^\]]*)\]\([^\)]+\)/g, '');
    text = text.replace(/^\s*[\*\-\+]\s+/gm, '');
    text = text.replace(/^\s*\d+\.\s+/gm, '');
    text = text.replace(/\n\n/g, '<br><br>');
    text = text.replace(/\n/g, '<br>');
    text = text.replace(/\s+/g, ' ').trim();

    return text;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function escapeForJs(text) {
    return text
        .replace(/\\/g, '\\\\')
        .replace(/'/g, "\\'")
        .replace(/"/g, '\\"')
        .replace(/\n/g, '\\n')
        .replace(/\r/g, '\\r');
}

function formatTime(date = new Date()) {
    return date.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
    });
}

function getRelativeTime(date) {
    const now = new Date();
    const diff = Math.floor((now - date) / 1000);

    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return date.toLocaleDateString();
}

function scrollToBottom(smooth = true) {
    const container = document.getElementById('chatMessages');
    if (!container) return;

    setTimeout(() => {
        container.scrollTo({
            top: container.scrollHeight,
            behavior: smooth ? 'smooth' : 'auto'
        });
    }, APP_CONFIG.autoScrollDelay);
}

function isScrolledToBottom() {
    const container = document.getElementById('chatMessages');
    if (!container) return true;

    const threshold = 100;
    return container.scrollHeight - container.scrollTop - container.clientHeight < threshold;
}

function handleMobileKeyboard() {
    const input = document.getElementById('userInput');
    if (!input) return;

    input.addEventListener('focus', () => {
        const glowWrapper = input.closest('.input-glow-wrapper');
        if (glowWrapper) glowWrapper.classList.add('focused');

        setTimeout(() => {
            scrollToBottom(false);
            input.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }, 300);
    });

    input.addEventListener('blur', () => {
        const glowWrapper = input.closest('.input-glow-wrapper');
        if (glowWrapper) glowWrapper.classList.remove('focused');
    });

    let lastHeight = window.innerHeight;
    window.addEventListener('resize', () => {
        const currentHeight = window.innerHeight;
        const diff = Math.abs(currentHeight - lastHeight);

        if (diff > 100) {
            setTimeout(() => {
                if (document.activeElement === input) scrollToBottom(false);
            }, 100);
        }

        lastHeight = currentHeight;
    });
}

async function copyToClipboard(text) {
    try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(text);
            showToast('Copied to clipboard', 'success', 2000);
            return true;
        } else {
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            document.body.appendChild(textarea);
            textarea.select();
            const success = document.execCommand('copy');
            document.body.removeChild(textarea);

            if (success) {
                showToast('Copied to clipboard', 'success', 2000);
                return true;
            } else {
                throw new Error('Copy failed');
            }
        }
    } catch (error) {
        console.error('[Clipboard]', error);
        showToast('Failed to copy', 'error', 2000);
        return false;
    }
}

function saveToStorage(key, value) {
    try {
        localStorage.setItem(key, JSON.stringify(value));
    } catch (e) {
        console.error('[Storage] Save failed:', e);
    }
}

function loadFromStorage(key, defaultValue = null) {
    try {
        const value = localStorage.getItem(key);
        return value ? JSON.parse(value) : defaultValue;
    } catch (e) {
        console.error('[Storage] Load failed:', e);
        return defaultValue;
    }
}

function removeFromStorage(key) {
    try {
        localStorage.removeItem(key);
    } catch (e) {
        console.error('[Storage] Remove failed:', e);
    }
}

function queueForRetry(type, data) {
    const queue = loadFromStorage('retryQueue', []);
    queue.push({ type, data, timestamp: Date.now() });
    saveToStorage('retryQueue', queue);
}

async function processRetryQueue() {
    const queue = loadFromStorage('retryQueue', []);
    if (queue.length === 0) return;

    console.log(`[Retry] Processing ${queue.length} items`);

    for (const item of queue) {
        try {
            if (item.type === 'report') {
                await fetch(`${API_BASE}/assistant/api/report/`, {
                    method: 'POST',
                    headers: getAPIHeaders(),
                    body: JSON.stringify(item.data)
                });
            }
        } catch (error) {
            console.error('[Retry] Failed:', error);
        }
    }

    removeFromStorage('retryQueue');
}

window.addEventListener('online', processRetryQueue);

document.addEventListener('DOMContentLoaded', () => {
    console.log('[App] v' + APP_CONFIG.version);

    initSession();
    initTheme();
    handleMobileKeyboard();

    trackEvent('page_view', {
        page: window.location.pathname,
        version: APP_CONFIG.version,
        theme: AppState.currentTheme
    });

    const hasOnboarded = loadFromStorage('gigiOnboarded', false);
    if (!hasOnboarded && typeof showOnboarding === 'function') {
        const isChatPage = window.location.pathname.includes('chat') || window.location.pathname.endsWith('/');
        if (isChatPage) setTimeout(showOnboarding, 800);
    }

    console.log('[App] Ready');
});

window.addEventListener('error', (e) => {
    console.error('[App] Error:', e.error);
    updateStatus('error', 'Something went wrong');
});

window.addEventListener('unhandledrejection', (e) => {
    console.error('[App] Unhandled rejection:', e.reason);
    updateStatus('error', 'Connection issue');
});