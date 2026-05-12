(function () {
    const livePanel = document.querySelector('[data-live-cashier-url]');
    const readyFeed = document.getElementById('cashier-ready-feed');
    const indicator = document.getElementById('cashier-live-indicator');

    if (!livePanel || !readyFeed) {
        return;
    }

    async function refreshCashierReadyOrders() {
        try {
            const response = await fetch(livePanel.dataset.liveCashierUrl, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
            });
            if (!response.ok) {
                throw new Error('Cashier refresh failed');
            }
            const data = await response.json();
            readyFeed.innerHTML = data.ready_orders_html;
            if (indicator) {
                indicator.textContent = `Live · ${data.ready_count} ready`;
                indicator.classList.remove('offline');
            }
        } catch (error) {
            if (indicator) {
                indicator.textContent = 'Reconnecting';
                indicator.classList.add('offline');
            }
        }
    }

    setInterval(refreshCashierReadyOrders, 3000);
    refreshCashierReadyOrders();
}());
