// Hermes CRM PWA JavaScript

// Register service worker
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/sw.js')
            .then(() => console.log('SW registered'))
            .catch(err => console.log('SW registration failed:', err));
    });
}

function showStatus(elementId, message, type) {
    const el = document.getElementById(elementId);
    if (el) {
        el.className = `status ${type}`;
        el.textContent = message;
        if (type !== 'hidden') {
            setTimeout(() => { el.className = 'status hidden'; }, 3000);
        }
    }
}
