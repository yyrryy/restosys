(function () {
    const drawer = document.getElementById('cashier-details-drawer');
    const overlay = document.getElementById('cashier-details-overlay');
    const cancelButton = document.getElementById('cashier-drawer-cancel');
    const orderIdEl = document.getElementById('drawer-order-id');
    const tableEl = document.getElementById('drawer-order-table');
    const statusEl = document.getElementById('drawer-order-status');
    const totalEl = document.getElementById('drawer-order-total');
    const itemsBody = document.getElementById('drawer-items-body');
    const receivedEl = document.getElementById('drawer-cash-received');
    const changeResult = document.getElementById('drawer-change-result');
    const changeNote = document.getElementById('drawer-change-note');
    const billGrid = document.getElementById('bill-grid');
    const undoButton = document.getElementById('bill-undo');
    const resetButton = document.getElementById('bill-reset');
    const detailsButtons = document.querySelectorAll('.cashier-details-trigger');
    const urlTemplate = window.cashierDetailsUrlTemplate;
    const paimentForm = document.querySelector('.paiment-form');
    if (
        !drawer || !overlay || !cancelButton || !orderIdEl || !tableEl || !statusEl || !totalEl ||
        !itemsBody || !receivedEl || !changeResult || !changeNote || !billGrid ||
        !undoButton || !resetButton || !detailsButtons.length || !urlTemplate
    ) {
        return;
    }

    let orderTotal = 0;
    let cashReceived = 0;
    const receivedBills = [];

    function formatMoney(value) {
        return Number(value || 0).toFixed(2);
    }

    function renderChange() {
        const change = cashReceived - orderTotal;
        receivedEl.textContent = formatMoney(cashReceived);
        changeResult.textContent = formatMoney(change);
        if (cashReceived === 0) {
            changeNote.textContent = 'Tap bills to calculate change.';
            return;
        }
        if (change < 0) {
            changeNote.textContent = `Missing ${formatMoney(Math.abs(change))} to complete payment.`;
            return;
        }
        changeNote.textContent = `Give ${formatMoney(change)} back to the customer.`;
    }

    function resetCalculator() {
        cashReceived = 0;
        receivedBills.length = 0;
        renderChange();
    }

    function buildItems(items) {
        if (!items.length) {
            itemsBody.innerHTML = '<tr><td colspan="4">No items found.</td></tr>';
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
        const detailsUrl = urlTemplate.replace('/0/details/', `/${orderId}/details/`);
        fetch(detailsUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error('Failed to fetch order details.');
                }
                return response.json();
            })
            .then(function (data) {
                orderIdEl.textContent = `#${data.id}`;
                tableEl.textContent = data.table;
                statusEl.textContent = data.status;
                orderTotal = Number(data.total || 0);
                paimentForm.action = "/orders/" + data.id + "/paid/";
                
                totalEl.textContent = formatMoney(orderTotal);
                buildItems(data.items || []);
                resetCalculator();
                openDrawer();

            })
            .catch(function () {
                changeNote.textContent = 'Failed to load order details.';
                openDrawer();
            });
    }

    detailsButtons.forEach(function (button) {
        button.addEventListener('click', function () {
            fetchDetails(button.dataset.orderId);
        });
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
    cancelButton.addEventListener('click', closeDrawer);
    overlay.addEventListener('click', closeDrawer);
    renderChange();
}());
