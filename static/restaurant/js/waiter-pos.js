(function () {
    const tabButtons = document.querySelectorAll('[data-tab-target]');
    const tabPanels = document.querySelectorAll('.tab-panel');
    const categoryButtons = document.querySelectorAll('[data-category]');
    const dishTiles = document.querySelectorAll('.dish-tile');
    const cartLines = document.getElementById('cart-lines');
    const cartTotal = document.getElementById('cart-total');
    const clearCartButton = document.getElementById('clear-cart');

    function activateTab(tabId) {
        tabButtons.forEach((button) => {
            button.classList.toggle('active', button.dataset.tabTarget === tabId);
        });
        tabPanels.forEach((panel) => {
            panel.classList.toggle('active', panel.id === tabId);
        });
    }

    function fieldForTile(tile) {
        return document.getElementById(tile.dataset.field);
    }

    function money(value) {
        return Number(value).toFixed(2);
    }

    function updateCart() {
        const lines = [];
        let total = 0;

        dishTiles.forEach((tile) => {
            const field = fieldForTile(tile);
            const quantity = Number(field ? field.value : 0);
            if (!quantity) {
                tile.classList.remove('selected');
                return;
            }

            tile.classList.add('selected');
            const price = Number(tile.dataset.price);
            total += quantity * price;
            lines.push({
                field,
                name: tile.dataset.name,
                quantity,
                price,
            });
        });

        if (!lines.length) {
            cartLines.innerHTML = '<p class="empty-state">Tap dishes to build the order.</p>';
            cartTotal.textContent = '0.00';
            return;
        }

        cartLines.innerHTML = lines.map((line) => `
            <div class="cart-line">
                <div>
                    <strong>${line.name}</strong>
                    <span>${line.quantity} x ${money(line.price)}</span>
                </div>
                <div class="qty-controls">
                    <button type="button" data-qty-step="-1" data-field="${line.field.id}">-</button>
                    <span>${line.quantity}</span>
                    <button type="button" data-qty-step="1" data-field="${line.field.id}">+</button>
                </div>
            </div>
        `).join('');
        cartTotal.textContent = money(total);
    }

    tabButtons.forEach((button) => {
        button.addEventListener('click', () => activateTab(button.dataset.tabTarget));
    });

    categoryButtons.forEach((button) => {
        button.addEventListener('click', () => {
            const category = button.dataset.category;
            categoryButtons.forEach((item) => item.classList.toggle('active', item === button));
            dishTiles.forEach((tile) => {
                tile.hidden = category !== 'all' && tile.dataset.category !== category;
            });
        });
    });

    dishTiles.forEach((tile) => {
        tile.addEventListener('click', () => {
            const field = fieldForTile(tile);
            if (!field) {
                return;
            }
            field.value = Number(field.value || 0) + 1;
            updateCart();
        });
    });

    cartLines.addEventListener('click', (event) => {
        const button = event.target.closest('[data-qty-step]');
        if (!button) {
            return;
        }
        const field = document.getElementById(button.dataset.field);
        const nextValue = Math.max(0, Number(field.value || 0) + Number(button.dataset.qtyStep));
        field.value = nextValue;
        updateCart();
    });

    clearCartButton.addEventListener('click', () => {
        dishTiles.forEach((tile) => {
            const field = fieldForTile(tile);
            if (field) {
                field.value = 0;
            }
        });
        updateCart();
    });

    activateTab(window.restoSysActiveOrderTab === 'manual' ? 'manual-tab' : 'pos-tab');
    updateCart();
}());
