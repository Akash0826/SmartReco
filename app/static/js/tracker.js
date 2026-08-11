/* 
static/js/tracker.js
====================

Responsibility:  Non-blocking frontend script that observes clicks/time and batches them to the API.

Pipeline Position: Client-Side (Browser)
*/

/**
 * SmartReco Behavioral Tracker
 * Captures user interactions and batches them to avoid blocking the main thread.
 */
class BehavioralTracker {
    constructor(userId) {
        this.userId = userId;
        this.eventQueue = [];
        this.batchInterval = 5000; // Flush every 5 seconds
        this.endpoint = '/api/tracking/batch';

        this.initListeners();
        this.startBatchTimer();

        // Track the initial page view
        this.track('page_view', { url: window.location.pathname });
        this.startTime = Date.now();
    }

    track(eventType, metadata = {}, productId = null) {
        this.eventQueue.push({
            event_type: eventType,
            product_id: productId,
            metadata_payload: metadata,
            timestamp: new Date().toISOString()
        });
    }

    initListeners() {
        // Track clicks on elements with the 'data-track-click' attribute
        document.addEventListener('click', (e) => {
            const trackableElement = e.target.closest('[data-track-click]');
            if (trackableElement) {
                const action = trackableElement.getAttribute('data-action') || 'click';
                const productId = trackableElement.getAttribute('data-product-id');
                this.track(action, { text: trackableElement.innerText }, productId);

                // Immediately flush when clicking a topic button
                this.flush();
            }
        });

        // Flush remaining events and track time spent when the user leaves the page
        window.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'hidden') {
                const timeSpent = Math.round((Date.now() - this.startTime) / 1000);
                this.track('time_on_page', { seconds: timeSpent });
                this.flush();
            }
        });
    }

    startBatchTimer() {
        setInterval(() => this.flush(), this.batchInterval);
    }

    flush() {
        if (this.eventQueue.length === 0 || !this.userId) return;

        const payload = JSON.stringify({
            user_id: parseInt(this.userId, 10),
            events: this.eventQueue
        });

        // Clear queue immediately
        this.eventQueue = [];

        // The reliable, modern way to send JSON that survives page navigation
        fetch(this.endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: payload,
            keepalive: true
        }).catch(console.error);
    }
}

// Initialize the tracker globally if the user ID is injected by Jinja
window.addEventListener('DOMContentLoaded', () => {
    const userId = window.SMARTRECO_USER_ID;
    if (userId) {
        window.tracker = new BehavioralTracker(userId);
    }
});