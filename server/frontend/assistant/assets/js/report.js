const MIN_DESCRIPTION_LENGTH = 10;

function validateEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function enableSubmitButton() {
    const form = document.getElementById('reportForm');
    const submitBtn = document.getElementById('submitBtn');
    if (!form || !submitBtn) return;

    const name = document.getElementById('name')?.value.trim();
    const email = document.getElementById('email')?.value.trim();
    const bugType = document.getElementById('bugType')?.value;
    const description = document.getElementById('description')?.value.trim();

    const isValid = name && 
                   email && 
                   validateEmail(email) && 
                   bugType && 
                   description && 
                   description.length >= MIN_DESCRIPTION_LENGTH;

    submitBtn.disabled = !isValid;
}

function showSuccess() {
    const form = document.getElementById('reportForm');
    const successMessage = document.getElementById('successMessage');

    if (form) form.style.display = 'none';
    if (successMessage) successMessage.classList.add('visible');

    if (typeof trackEvent === 'function') {
        trackEvent('bug_report_submitted');
    }
}

function hideSuccess() {
    const form = document.getElementById('reportForm');
    const successMessage = document.getElementById('successMessage');

    if (form) form.style.display = 'block';
    if (successMessage) successMessage.classList.remove('visible');
}

function resetForm() {
    const form = document.getElementById('reportForm');
    if (form) form.reset();
    
    const submitBtn = document.getElementById('submitBtn');
    if (submitBtn) submitBtn.disabled = true;
}

async function handleSubmit(e) {
    e.preventDefault();

    const submitBtn = document.getElementById('submitBtn');
    const submitText = document.getElementById('submitText');

    if (!submitBtn || !submitText) return;

    const formData = {
        name: document.getElementById('name')?.value.trim(),
        email: document.getElementById('email')?.value.trim(),
        bug_type: document.getElementById('bugType')?.value,
        description: document.getElementById('description')?.value.trim(),
        steps: document.getElementById('steps')?.value.trim(),
        device: document.getElementById('device')?.value.trim()
    };

    if (!formData.name || !formData.email || !formData.bug_type || !formData.description) {
        if (typeof showToast === 'function') {
            showToast('Please fill in all required fields', 'warning');
        }
        return;
    }

    if (!validateEmail(formData.email)) {
        if (typeof showToast === 'function') {
            showToast('Please enter a valid email address', 'warning');
        }
        return;
    }

    if (formData.description.length < MIN_DESCRIPTION_LENGTH) {
        if (typeof showToast === 'function') {
            showToast(`Description must be at least ${MIN_DESCRIPTION_LENGTH} characters`, 'warning');
        }
        return;
    }

    submitBtn.disabled = true;
    submitText.innerHTML = '<span class="spinner"></span> Submitting...';

    try {
        const headers = typeof getAPIHeaders === 'function' 
            ? getAPIHeaders() 
            : { 'Content-Type': 'application/json' };

        const apiBase = typeof API_BASE !== 'undefined' ? API_BASE : '';

        const response = await fetch(`${apiBase}/assistant/api/report/`, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify(formData)
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        console.log('[Report] Submitted successfully:', data);

        showSuccess();
        resetForm();

        if (typeof trackEvent === 'function') {
            trackEvent('bug_report_success', {
                bug_type: formData.bug_type,
                has_steps: !!formData.steps,
                has_device: !!formData.device
            });
        }

    } catch (error) {
        console.error('[Report] Submission error:', error);

        if (typeof queueForRetry === 'function') {
            queueForRetry('report', formData);
        }

        submitBtn.disabled = false;
        submitText.textContent = 'Submit Report';

        if (typeof showToast === 'function') {
            showToast('Failed to submit report. It will be retried when you reconnect.', 'error', 5000);
        } else {
            alert('Failed to submit report. Please try again or check your connection.');
        }

        if (typeof trackEvent === 'function') {
            trackEvent('bug_report_failed', { error: error.message });
        }
    }
}

function setupReportListeners() {
    const form = document.getElementById('reportForm');
    if (form) {
        form.addEventListener('submit', handleSubmit);
    }

    const inputs = ['name', 'email', 'bugType', 'description'];
    inputs.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.addEventListener('input', enableSubmitButton);
            element.addEventListener('change', enableSubmitButton);
        }
    });

    const submitBtn = document.getElementById('submitBtn');
    if (submitBtn) {
        submitBtn.disabled = true;
    }

    console.log('[Report] Form initialized');
}

document.addEventListener('DOMContentLoaded', () => {
    if (!document.getElementById('reportForm')) return;
    
    setupReportListeners();
    
    if (typeof trackEvent === 'function') {
        trackEvent('bug_report_page_viewed');
    }
});