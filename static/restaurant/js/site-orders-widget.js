(function () {
    const widget = document.getElementById('site-orders-widget');
    const toggle = document.getElementById('site-orders-toggle');
    const panel = document.getElementById('site-orders-panel');
    const badge = document.getElementById('site-orders-badge');
    const list = document.getElementById('site-orders-list');

    if (!widget || !toggle || !panel || !list) {
        return;
    }

    const feedUrl = widget.dataset.feedUrl;
    let expanded = false;
    let newOrderAudio = null;
    
    function togglePanel() {
        if (newOrderAudio) {
            newOrderAudio.pause();
            newOrderAudio.currentTime = 0;
            newOrderAudio = null;
        }
        expanded = !expanded;
        panel.hidden = !expanded;
        widget.classList.toggle('expanded', expanded);
        if (expanded) {
            refreshOrders();
        }
    }

    function formatTotal(value) {
        const number = Number(value || 0);
        return number.toFixed(2);
    }

    function renderOrders(orders) {
        if (!orders || orders.length === 0) {
            list.innerHTML = '<p class="site-orders-empty">Aucune commande pour le moment.</p>';
            return;
        }

        list.innerHTML = orders.map(function (order) {
            const label = order.order_no || order.clientname || `Commande #${order.id}`;
            const items = (order.items || []).map(function (item) {
                return `<li>${item.qty} x ${item.name} - ${formatTotal(item.total)} DH</li>`;
            }).join('');

            return `
                <div class="site-order-card">
                    <div class="site-order-card-head">
                        <span>${label}</span>
                        <span class="site-order-card-total">${formatTotal(order.total)} DH</span>
                        <button onclick='printserverorder(${order.id}, event)'>Imprimer</button>
                    </div>
                    ${order.clientname ? `<p class="site-order-card-meta">${order.clientname}${order.clientphone ? ' - ' + order.clientphone : ''}</p>` : ''}
                    ${items ? `<ul class="site-order-card-items">${items}</ul>` : ''}
                </div>
            `;
        }).join('');
    }

    function updateBadge(count) {
        if (count > 0) {
            badge.textContent = String(count);
            badge.hidden = false;
        } else {
            badge.hidden = true;
        }
    }

    async function refreshOrders() {
        if (!feedUrl) {
            return;
        }
        try {
            const response = await fetch(feedUrl, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                cache: 'no-store',
            });
            if (!response.ok) {
                throw new Error('Site orders request failed');
            }
            const data = await response.json();
            updateBadge(Number(data.count || 0));
            if (data.neworders) {
                // Loop the alert until the user clicks the widget.
                if (!newOrderAudio) {
                    newOrderAudio = new Audio('/static/sounds/notificationsound.mp3');
                    newOrderAudio.loop = true;
                    newOrderAudio.play().catch(function () {});
                }
                
            }
            if (expanded) {
                renderOrders(data.orders || []);
            }
        } catch (error) {
            console.error('Error fetching site orders:', error);
        }
    }

    toggle.addEventListener('click', togglePanel);
    refreshOrders();
    window.setInterval(refreshOrders, 5000);
}());
