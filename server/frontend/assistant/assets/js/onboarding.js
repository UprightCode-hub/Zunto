/**
 * GigiAI - Onboarding Module
 * Multi-slide onboarding modal
 */

// ============================================
// ONBOARDING DATA
// ============================================
const ONBOARDING_SLIDES = [
    {
        icon: '👋',
        title: 'Welcome to GigiAI',
        text: 'Your intelligent e-commerce assistant powered by AI. Get instant help with orders, shipping, refunds, and more!'
    },
    {
        icon: '💬',
        title: 'Smart Conversations',
        text: 'Follow guided prompts to quickly resolve issues. Track orders, get shipping info, or request refunds in seconds.'
    },
    {
        icon: '🎙️',
        title: 'Voice Features',
        text: 'Listen to responses with text-to-speech. Perfect for multitasking or accessibility. Toggle voice on/off anytime.'
    },
    {
        icon: '🚀',
        title: 'Ready to Start?',
        text: 'Type your message or choose from quick suggestions. GigiAI is here to help 24/7!'
    }
];

// ============================================
// STATE
// ============================================
let currentSlide = 0;

// ============================================
// SHOW/HIDE ONBOARDING
// ============================================

function showOnboarding() {
    currentSlide = 0;
    
    if (!document.getElementById('onboardingOverlay')) {
        createOnboardingModal();
    }
    
    const overlay = document.getElementById('onboardingOverlay');
    if (overlay) {
        overlay.classList.add('visible');
        renderSlide(currentSlide);
        if (typeof trackEvent === 'function') {
            trackEvent('onboarding_started');
        }
    }
}

function hideOnboarding() {
    const overlay = document.getElementById('onboardingOverlay');
    if (overlay) {
        overlay.classList.remove('visible');
    }
}

function completeOnboarding() {
    hideOnboarding();
    if (typeof saveToStorage === 'function') {
        saveToStorage('gigiOnboarded', true);
    }
    if (typeof trackEvent === 'function') {
        trackEvent('onboarding_completed');
    }
    if (typeof showToast === 'function') {
        showToast('Welcome aboard! Start chatting below.', 'success');
    }
}

function skipOnboarding() {
    hideOnboarding();
    if (typeof saveToStorage === 'function') {
        saveToStorage('gigiOnboarded', true);
    }
    if (typeof trackEvent === 'function') {
        trackEvent('onboarding_skipped');
    }
}

// ============================================
// NAVIGATION
// ============================================

function nextSlide() {
    if (currentSlide < ONBOARDING_SLIDES.length - 1) {
        currentSlide++;
        renderSlide(currentSlide);
        if (typeof trackEvent === 'function') {
            trackEvent('onboarding_next', { slide: currentSlide });
        }
    } else {
        completeOnboarding();
    }
}

function prevSlide() {
    if (currentSlide > 0) {
        currentSlide--;
        renderSlide(currentSlide);
        if (typeof trackEvent === 'function') {
            trackEvent('onboarding_prev', { slide: currentSlide });
        }
    }
}

function goToSlide(index) {
    if (index >= 0 && index < ONBOARDING_SLIDES.length) {
        currentSlide = index;
        renderSlide(currentSlide);
    }
}

// ============================================
// RENDERING
// ============================================

function renderSlide(index) {
    const slides = document.querySelectorAll('.onboarding-slide');
    const dots = document.querySelectorAll('.onboarding-dot');
    
    slides.forEach((slide, i) => {
        slide.classList.toggle('active', i === index);
    });
    
    dots.forEach((dot, i) => {
        dot.classList.toggle('active', i === index);
    });
}

function createOnboardingModal() {
    const html = `
        <div class="onboarding-overlay" id="onboardingOverlay">
            <div class="onboarding-modal">
                ${ONBOARDING_SLIDES.map((slide, index) => `
                    <div class="onboarding-slide ${index === 0 ? 'active' : ''}" data-slide="${index}">
                        <div class="onboarding-icon">${slide.icon}</div>
                        <h2 class="onboarding-title">${slide.title}</h2>
                        <p class="onboarding-text">${slide.text}</p>
                        
                        <div class="onboarding-dots">
                            ${ONBOARDING_SLIDES.map((_, i) => `
                                <div class="onboarding-dot ${i === index ? 'active' : ''}" 
                                     onclick="goToSlide(${i})"
                                     aria-label="Go to slide ${i + 1}">
                                </div>
                            `).join('')}
                        </div>
                        
                        <div class="onboarding-actions">
                            ${index > 0 ? `
                                <button class="btn btn-ghost" onclick="prevSlide()" aria-label="Previous">
                                    <i class="bi bi-arrow-left"></i> Back
                                </button>
                            ` : `
                                <button class="btn btn-ghost" onclick="skipOnboarding()" aria-label="Skip onboarding">
                                    Skip
                                </button>
                            `}
                            
                            ${index < ONBOARDING_SLIDES.length - 1 ? `
                                <button class="btn btn-primary" onclick="nextSlide()" aria-label="Next">
                                    Next <i class="bi bi-arrow-right"></i>
                                </button>
                            ` : `
                                <button class="btn btn-primary" onclick="completeOnboarding()" aria-label="Start using GigiAI">
                                    Start Chat <i class="bi bi-chat-dots"></i>
                                </button>
                            `}
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', html);
    
    // Close on overlay click
    const overlay = document.getElementById('onboardingOverlay');
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            skipOnboarding();
        }
    });
    
    // Close on Escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && overlay.classList.contains('visible')) {
            skipOnboarding();
        }
    });
}

// ============================================
// RESET ONBOARDING
// ============================================

function resetOnboarding() {
    if (typeof removeFromStorage === 'function') {
        removeFromStorage('gigiOnboarded');
    }
    showOnboarding();
    if (typeof trackEvent === 'function') {
        trackEvent('onboarding_reset');
    }
}

// ============================================
// AUTO-INITIALIZE
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    // Check if should show onboarding
    const hasOnboarded = typeof loadFromStorage === 'function' 
        ? loadFromStorage('gigiOnboarded', false) 
        : false;
    
    // Only show on chat page
    const isChatPage = window.location.pathname.includes('chat') || 
                       window.location.pathname.endsWith('/');
    
    if (!hasOnboarded && isChatPage) {
        setTimeout(showOnboarding, 800);
    }
});
