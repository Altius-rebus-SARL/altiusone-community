/**
 * AltiusOne Web Push Notifications
 * Handles VAPID-based Web Push subscription and registration.
 * Only activates if push notifications are enabled on the instance.
 */
(function () {
  'use strict';

  const REGISTER_URL = '/api/v1/core/users/devices/register/';
  const UNREGISTER_URL = '/api/v1/core/users/devices/unregister/';
  const CONFIG_URL = '/api/v1/core/users/push/config/';
  const SW_PATH = '/sw-push.js';
  const STORAGE_KEY = 'push_subscription_endpoint';

  /**
   * Check if push notifications are supported and enabled.
   */
  async function init() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
      console.log('Push notifications not supported in this browser');
      return;
    }

    try {
      // Check if push is enabled on this instance
      const resp = await fetch(CONFIG_URL, { credentials: 'same-origin' });
      if (!resp.ok) return;

      const config = await resp.json();
      if (!config.enabled || !config.vapid_public_key) {
        console.log('Push notifications not enabled on this instance');
        return;
      }

      // Register service worker
      const registration = await navigator.serviceWorker.register(SW_PATH);
      console.log('Push SW registered:', registration.scope);

      // Check existing subscription
      const existing = await registration.pushManager.getSubscription();
      if (existing) {
        console.log('Already subscribed to push');
        return;
      }

      // Expose subscribe function for UI buttons
      window.AltiusOnePush = {
        subscribe: () => subscribeToPush(registration, config.vapid_public_key),
        unsubscribe: () => unsubscribeFromPush(registration),
        isSupported: true,
        isSubscribed: !!existing,
      };

    } catch (err) {
      console.warn('Push init error:', err);
    }
  }

  /**
   * Subscribe to push notifications.
   */
  async function subscribeToPush(registration, vapidPublicKey) {
    try {
      const permission = await Notification.requestPermission();
      if (permission !== 'granted') {
        console.log('Push permission denied');
        return false;
      }

      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
      });

      // Send subscription to backend
      const csrfToken = getCsrfToken();
      const resp = await fetch(REGISTER_URL, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({
          token: JSON.stringify(subscription.toJSON()),
          device_type: 'web',
          name: getBrowserName(),
        }),
      });

      if (resp.ok) {
        localStorage.setItem(STORAGE_KEY, subscription.endpoint);
        if (window.AltiusOnePush) window.AltiusOnePush.isSubscribed = true;
        console.log('Subscribed to push notifications');
        return true;
      }
      return false;

    } catch (err) {
      console.error('Subscribe error:', err);
      return false;
    }
  }

  /**
   * Unsubscribe from push notifications.
   */
  async function unsubscribeFromPush(registration) {
    try {
      const subscription = await registration.pushManager.getSubscription();
      if (!subscription) return true;

      // Notify backend
      const csrfToken = getCsrfToken();
      await fetch(UNREGISTER_URL, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({
          token: JSON.stringify(subscription.toJSON()),
        }),
      });

      await subscription.unsubscribe();
      localStorage.removeItem(STORAGE_KEY);
      if (window.AltiusOnePush) window.AltiusOnePush.isSubscribed = false;
      console.log('Unsubscribed from push notifications');
      return true;

    } catch (err) {
      console.error('Unsubscribe error:', err);
      return false;
    }
  }

  /**
   * Convert VAPID key from base64 to Uint8Array.
   */
  function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  }

  /**
   * Get CSRF token from cookie.
   */
  function getCsrfToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : '';
  }

  /**
   * Get a readable browser name.
   */
  function getBrowserName() {
    const ua = navigator.userAgent;
    if (ua.includes('Chrome')) return 'Chrome';
    if (ua.includes('Firefox')) return 'Firefox';
    if (ua.includes('Safari')) return 'Safari';
    if (ua.includes('Edge')) return 'Edge';
    return 'Web Browser';
  }

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
