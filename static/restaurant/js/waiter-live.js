(function () {
    const livePanel = document.querySelector('[data-live-waiter-url]');
    const readyFeed = document.getElementById('waiter-ready-feed');
    const ordersFeed = document.getElementById('waiter-orders-feed');
    const indicator = document.getElementById('waiter-live-indicator');

    if (!livePanel || !readyFeed || !ordersFeed) {
        return;
    }

    async function refreshWaiterOrders() {
        try {
            const response = await fetch(livePanel.dataset.liveWaiterUrl, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
            });
            if (!response.ok) {
                throw new Error('Waiter refresh failed');
            }
            const data = await response.json();
            console.log('Waiter live data:', data);
            readyFeed.innerHTML = data.ready_alerts_html;
            ordersFeed.innerHTML = data.orders_html;
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

    setInterval(refreshWaiterOrders, 3000);
    refreshWaiterOrders();
}());
