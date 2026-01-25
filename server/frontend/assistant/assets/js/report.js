/**
 * GigiAI - Report Module
 * Handles bug report submission
 * API: POST ${API_BASE}/assistant/api/report/
 */

// ============================================
// REPORT SUBMISSION
// ============================================

/**
 * Handle report form submission
 * @param {Event} event - Form submit event
 */
async function handleReportSubmit(event) {
    event.preventDefault();
    
    const form = document.getElementById('reportForm');
    const successMessage = document.getElementById('successMessage');
    const submitBtn = document.getElementById('submitBtn');
    const submitText = document.getElementById('submitText');
    
    if (!form || !successMessage || !submitBtn) return;
    
    // Disable submit button
    submitBtn.disabled = true;
    submitText.innerHTML = '<span class="spinner"></span> Submitting...';
    
    // Collect form data
    const formData = {
        name: document.getElementById('name').value.trim(),
        email: document.getElementById('email').value.trim(),
        bugType: document.getElementById('bugType').value,
        description: document.getElementById('description').value.trim(),
        steps: document.getElementById('steps').value.trim() || 'Not provided',
        device: document.getElementById('device').value.trim() || 'Not provided',
        timestamp: new Date().toISOString(),
        url: window.location.href,
        userAgent: navigator.userAgent
    };
    
    console.log('[Report] Submitting bug report:', formData);
    
    try {
        // API call - DO NOT MODIFY ENDPOINT
        const response = await fetch(`${API_BASE}/assistant/api/report/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // Success - hide form and show success message
        form.style.display = 'none';
        successMessage.classList.add('visible');
        
        // Track event
        if (typeof trackEvent === 'function') {
            trackEvent('bug_reported', { type: formData.bugType });
        }
        
        console.log('[Report] Success:', data);
        
    } catch (error) {
        console.error('[Report] Error:', error);
        
        // Re-enable button
        submitBtn.disabled = false;
        submitText.textContent = 'Submit Report';
        
        // Check if offline
        if (!navigator.onLine) {
            // Queue for retry when online
            if (typeof queueForRetry === 'function') {
                queueForRetry('report', formData);
                showSuccessWithQueue(form, successMessage);
            } else {
                showError('You are offline. Please try again when connected.');
            }
        } else {
            // Show error message
            showError(`Failed to submit report: ${error.message}. Please try again or contact support.`);
        }
    }
}

/**
 * Show success message for queued report
 */
function showSuccessWithQueue(form, successMessage) {
    form.style.display = 'none';
    successMessage.classList.add('visible');
    
    const successTitle = successMessage.querySelector('h2');
    const successText = successMessage.querySelector('p');
    
    if (successTitle) {
        successTitle.textContent = 'Report Queued';
    }
    
    if (successText) {
        successText.textContent = 'You are currently offline. Your report has been saved and will be submitted automatically when you reconnect.';
    }
    
    console.log('[Report] Queued for retry');
}

/**
 * Show error message
 */
function showError(message) {
    const errorDiv = document.getElementById('reportError');
    
    if (!errorDiv) {
        // Create error div if it doesn't exist
        const form = document.getElementById('reportForm');
        if (form) {
            const error = document.createElement('div');
            error.id = 'reportError';
            error.style.cssText = `
                background: rgba(239, 68, 68, 0.1);
                border: 2px solid var(--danger);
                border-radius: var(--radius);
                padding: 1rem;
                margin-bottom: 1rem;
                color: var(--danger);
                font-weight: 600;
            `;
            error.textContent = message;
            form.insertBefore(error, form.firstChild);
            
            // Auto-hide after 5 seconds
            setTimeout(() => {
                error.remove();
            }, 5000);
        }
    } else {
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
        
        setTimeout(() => {
            errorDiv.style.display = 'none';
        }, 5000);
    }
}

// ============================================
// FORM VALIDATION
// ============================================

/**
 * Real-time form validation
 */
function validateReportForm() {
    const name = document.getElementById('name');
    const email = document.getElementById('email');
    const bugType = document.getElementById('bugType');
    const description = document.getElementById('description');
    const submitBtn = document.getElementById('submitBtn');
    
    if (!name || !email || !bugType || !description || !submitBtn) return;
    
    const isValid = 
        name.value.trim().length > 0 &&
        email.value.trim().length > 0 &&
        email.value.includes('@') &&
        bugType.value !== '' &&
        description.value.trim().length > 10;
    
    submitBtn.disabled = !isValid;
}

/**
 * Setup form validation listeners
 */
function setupReportValidation() {
    const fields = ['name', 'email', 'bugType', 'description'];
    
    fields.forEach(fieldId => {
        const field = document.getElementById(fieldId);
        if (field) {
            field.addEventListener('input', validateReportForm);
            field.addEventListener('change', validateReportForm);
        }
    });
    
    // Initial validation
    validateReportForm();
}

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    // Only run on report page
    if (!document.getElementById('reportForm')) return;
    
    console.log('[Report] Initializing...');
    
    // Setup form submit handler
    const form = document.getElementById('reportForm');
    if (form) {
        form.addEventListener('submit', handleReportSubmit);
    }
    
    // Setup validation
    setupReportValidation();
    
    console.log('[Report] Ready');
});
