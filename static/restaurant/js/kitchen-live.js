(function () {
    const livePanel = document.querySelector('[data-live-kitchen-url]');
    const ordersFeed = document.getElementById('kitchen-orders-feed');
    const readyFeed = document.getElementById('kitchen-ready-feed');
    const indicator = document.getElementById('kitchen-live-indicator');

    if (!livePanel || !ordersFeed || !readyFeed) {
        return;
    }

    async function refreshKitchenOrders() {
        try {
            const response = await fetch(livePanel.dataset.liveKitchenUrl, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
            });
            if (!response.ok) {
                throw new Error('Kitchen refresh failed');
            }
            const data = await response.json();
            console.log('Kitchen live data:', data);
            console.log('Kitchen live data:', data);
            ordersFeed.innerHTML = data.orders_html;
            readyFeed.innerHTML = data.ready_orders_html;
            if (indicator) {
                indicator.textContent = `Live · ${data.open_count} open`;
                indicator.classList.remove('offline');
            }
        } catch (error) {
            if (indicator) {
                indicator.textContent = 'Reconnecting';
                indicator.classList.add('offline');
            }
        }
    }

    setInterval(refreshKitchenOrders, 3000);
    refreshKitchenOrders();
}());
