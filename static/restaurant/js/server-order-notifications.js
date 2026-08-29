(function () {
    const endpoint = window.serverOrderNotificationUrl;
    const banner = document.getElementById('server-order-notification');
    const countText = document.getElementById('server-order-notification-count');
    const enableSoundButton = document.getElementById('enable-order-sound');

    if (!endpoint || !banner) {
        return;
    }

    const storageKey = 'restosys-last-server-order-notification';
    let lastNotificationId = Number.parseInt(localStorage.getItem(storageKey) || '0', 10);
    let audioContext = null;

    function updateEnableButton() {
        if (!enableSoundButton) {
            return;
        }
        if (window.Notification && Notification.permission === 'granted') {
            enableSoundButton.textContent = 'Notifications enabled';
            enableSoundButton.disabled = true;
        } else {
            enableSoundButton.textContent = 'Enable notifications';
            enableSoundButton.disabled = false;
        }
    }

    function enableSound() {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (AudioContext) {
            audioContext = audioContext || new AudioContext();
            if (audioContext.state === 'suspended') {
                audioContext.resume();
            }
        }

        // Once granted, the browser remembers this permission for the origin
        // across future visits, so notifications (with sound) fire automatically
        // without needing another click.
        if (window.Notification && Notification.permission !== 'granted' && Notification.permission !== 'denied') {
            Notification.requestPermission().then(updateEnableButton);
        } else {
            updateEnableButton();
        }
    }

    function playOrderSound() {
        if (!audioContext) {
            return;
        }
        const oscillator = audioContext.createOscillator();
        const gain = audioContext.createGain();
        oscillator.type = 'sine';
        oscillator.frequency.setValueAtTime(880, audioContext.currentTime);
        oscillator.frequency.setValueAtTime(660, audioContext.currentTime + 0.18);
        gain.gain.setValueAtTime(0.0001, audioContext.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.25, audioContext.currentTime + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0001, audioContext.currentTime + 0.45);
        oscillator.connect(gain);
        gain.connect(audioContext.destination);
        oscillator.start();
        oscillator.stop(audioContext.currentTime + 0.45);
    }

    function showNotification(count) {
        countText.textContent = `${count} order${count === 1 ? '' : 's'} received`;
        banner.hidden = false;
        playOrderSound();
        window.setTimeout(function () {
            banner.hidden = true;
        }, 8000);

        // Fires a system notification (with the OS default sound) automatically
        // once permission has been granted, with no user gesture required.
        if (window.Notification && Notification.permission === 'granted') {
            const notification = new Notification('New online order', {
                body: `${count} order${count === 1 ? '' : 's'} received`,
                tag: 'restosys-server-order',
                renotify: true,
            });
            notification.onclick = function () {
                window.focus();
                notification.close();
            };
        }
    }

    async function checkForOrders() {
        try {
            const response = await fetch(endpoint, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                cache: 'no-store',
            });
            if (!response.ok) {
                throw new Error('Order notification request failed');
            }
            const data = await response.json();
            const notificationId = Number(data.notification_id || 0);

            if (lastNotificationId === 0) {
                lastNotificationId = notificationId;
                localStorage.setItem(storageKey, String(lastNotificationId));
                if (Number(data.new_count || 0) > 0) {
                    showNotification(Number(data.new_count));
                }
                return;
            }

            if (notificationId > lastNotificationId) {
                lastNotificationId = notificationId;
                localStorage.setItem(storageKey, String(lastNotificationId));
                showNotification(Number(data.length || 1));
            }
        } catch (error) {
            console.error('Error checking online orders:', error);
        }
    }

    enableSoundButton.addEventListener('click', enableSound);
    document.addEventListener('click', enableSound, { once: true });
    updateEnableButton();
    checkForOrders();
    window.setInterval(checkForOrders, 3000);
}());
