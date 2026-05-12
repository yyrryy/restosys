(function () {
    const drawer = document.getElementById('cashier-details-drawer');
    const overlay = document.getElementById('cashier-details-overlay');
    const cancelButton = document.getElementById('cashier-drawer-cancel');
    const orderIdEl = document.getElementById('drawer-order-id');
    const tableEl = document.getElementById('drawer-order-table');
    const statusEl = document.getElementById('drawer-order-status');
    const subtotalEl = document.getElementById('drawer-order-subtotal');
    const totalEl = document.getElementById('drawer-order-total');
    const itemsBody = document.getElementById('drawer-items-body');
    const receivedEl = document.getElementById('drawer-cash-received');
    const changeResult = document.getElementById('drawer-change-result');
    const changeNote = document.getElementById('drawer-change-note');
    const billGrid = document.getElementById('bill-grid');
    const undoButton = document.getElementById('bill-undo');
    const resetButton = document.getElementById('bill-reset');
    const orderDetailsUrlTemplate = window.cashierOrderDetailsUrlTemplate;
    const tableDetailsUrlTemplate = window.cashierTableDetailsUrlTemplate;
    const orderPayUrlTemplate = window.cashierOrderPayUrlTemplate;
    const tablePayUrlTemplate = window.cashierTablePayUrlTemplate;
    const paimentForm = document.querySelector('.paiment-form');
    const discountInput = document.getElementById('drawer-discount-input');
    if (
        !drawer || !overlay || !cancelButton || !orderIdEl || !tableEl || !statusEl || !subtotalEl || !totalEl ||
        !itemsBody || !receivedEl || !changeResult || !changeNote || !billGrid ||
        !undoButton || !resetButton || !orderDetailsUrlTemplate ||
        !tableDetailsUrlTemplate || !orderPayUrlTemplate || !tablePayUrlTemplate || !discountInput
    ) {
        return;
    }

    let orderTotal = 0;
    let cashReceived = 0;
    const receivedBills = [];

    function formatMoney(value) {
        return Number(value || 0).toFixed(2);
    }

    function updateDiscountDisplay() {
        const subtotal = Number(subtotalEl.dataset.value || 0);
        const parsedValue = Number(discountInput.value);
        const rawValue = Number.isFinite(parsedValue) ? parsedValue : 0;
        const discountAmount = Math.max(0, Math.min(rawValue, subtotal));
        orderTotal = subtotal - discountAmount;
        totalEl.textContent = formatMoney(orderTotal);
        renderChange();
    }

    function renderChange() {
        const change = cashReceived - orderTotal;
        receivedEl.textContent = formatMoney(cashReceived);
        changeResult.textContent = formatMoney(change);
        if (cashReceived === 0) {
            changeNote.textContent = 'Touchez les billets pour calculer la monnaie.';
            return;
        }
        if (change < 0) {
            changeNote.textContent = `Il manque ${formatMoney(Math.abs(change))} pour finaliser le paiement.`;
            return;
        }
        changeNote.textContent = `Rendez ${formatMoney(change)} au client.`;
    }

    function resetCalculator() {
        cashReceived = 0;
        receivedBills.length = 0;
        renderChange();
    }

    function buildItems(items) {
        if (!items.length) {
            itemsBody.innerHTML = '<tr><td colspan="4">Aucun article trouvé.</td></tr>';
            return;
        }
        itemsBody.innerHTML = '';
        items.forEach(function (item) {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${item.name}</td>
                <td>${item.quantity}</td>
                <td>${formatMoney(item.unit_price)}</td>
                <td>${formatMoney(item.line_total)}</td>
            `;
            itemsBody.appendChild(row);
        });
    }

    function openDrawer() {
        drawer.classList.add('open');
        overlay.classList.add('open');
    }

    function closeDrawer() {
        drawer.classList.remove('open');
        overlay.classList.remove('open');
    }

    function fetchDetails(orderId) {
        const detailsUrl = orderDetailsUrlTemplate.replace('/0/', `/${orderId}/`);
        fetch(detailsUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error('Échec du chargement des détails de commande.');
                }
                return response.json();
            })
            .then(function (data) {
                orderIdEl.textContent = data.order_label || `#${data.id}`;
                tableEl.textContent = data.table;
                statusEl.textContent = data.status;
                const subtotal = Number(data.subtotal || 0);
                subtotalEl.dataset.value = String(subtotal);
                subtotalEl.textContent = formatMoney(subtotal);
                discountInput.value = formatMoney(Number(data.discount_amount || 0));
                paimentForm.action = orderPayUrlTemplate.replace('/0/', `/${data.id}/`);
                buildItems(data.items || []);
                resetCalculator();
                updateDiscountDisplay();
                openDrawer();

            })
            .catch(function () {
                changeNote.textContent = 'Échec du chargement des détails de commande.';
                openDrawer();
            });
    }

    function fetchTableDetails(tableId) {
        const detailsUrl = tableDetailsUrlTemplate.replace('/0/', `/${tableId}/`);
        fetch(detailsUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error('Échec du chargement des détails de paiement table.');
                }
                return response.json();
            })
            .then(function (data) {
                orderIdEl.textContent = data.order_label || '-';
                tableEl.textContent = data.table;
                statusEl.textContent = data.status;
                const subtotal = Number(data.subtotal || 0);
                subtotalEl.dataset.value = String(subtotal);
                subtotalEl.textContent = formatMoney(subtotal);
                discountInput.value = formatMoney(Number(data.discount_amount || 0));
                paimentForm.action = tablePayUrlTemplate.replace('/0/', `/${data.id}/`);
                buildItems(data.items || []);
                resetCalculator();
                updateDiscountDisplay();
                openDrawer();
            })
            .catch(function () {
                changeNote.textContent = 'Échec du chargement des détails de paiement table.';
                openDrawer();
            });
    }

    document.addEventListener('click', function (event) {
        const button = event.target.closest('.cashier-details-trigger');
        if (!button) {
            return;
        }
        const tableId = button.dataset.tableId;
        if (tableId) {
            fetchTableDetails(tableId);
            return;
        }
        fetchDetails(button.dataset.orderId);
    });

    billGrid.addEventListener('click', function (event) {
        const bill = event.target.closest('.bill-button');
        if (!bill) {
            return;
        }
        const value = Number(bill.dataset.value || 0);
        if (value <= 0) {
            return;
        }
        receivedBills.push(value);
        cashReceived += value;
        renderChange();
    });

    undoButton.addEventListener('click', function () {
        if (!receivedBills.length) {
            return;
        }
        cashReceived -= receivedBills.pop();
        renderChange();
    });

    resetButton.addEventListener('click', resetCalculator);
    discountInput.addEventListener('input', updateDiscountDisplay);
    cancelButton.addEventListener('click', closeDrawer);
    overlay.addEventListener('click', closeDrawer);
    renderChange();
}());
