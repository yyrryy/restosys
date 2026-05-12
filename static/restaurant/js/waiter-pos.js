(function () {
    const tabButtons = document.querySelectorAll('[data-tab-target]');
    const tabPanels = document.querySelectorAll('.tab-panel');
    const categoryButtons = document.querySelectorAll('[data-category]');
    const dishTiles = document.querySelectorAll('.dish-tile');
    const cartLines = document.getElementById('cart-lines');
    const cartTotal = document.getElementById('cart-total');
    const clearCartButton = document.getElementById('clear-cart');
    const barcodeStatsByFieldId = {};
    const resolvedItemIdByPlu = {};
    const itemLastTouchedByFieldId = {};
    let touchSequence = 0;
    const resolvePluUrl = window.posResolvePluUrl || '';

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

    function parseScaleBarcode(rawValue) {
        const digits = String(rawValue || '').replace(/\D/g, '');
        if (digits.length >= 12) {
            return {
                plu: Number(digits.slice(2, 7)),
                barcodePrice: Number(digits.slice(7, 12)) / 100,
            };
        }
        if (digits.length >= 1) {
            return {
                plu: Number(digits),
                barcodePrice: null,
            };
        }
        return {
            plu: 0,
            barcodePrice: null,
        };
    }

    function roundWeight(value) {
        return Math.round(Number(value || 0) * 1000) / 1000;
    }

    function markFieldTouched(fieldId) {
        touchSequence += 1;
        itemLastTouchedByFieldId[fieldId] = touchSequence;
    }

    async function resolveItemIdByPlu(plu) {
        if (!plu || !resolvePluUrl) {
            return 0;
        }
        if (resolvedItemIdByPlu[String(plu)]) {
            return resolvedItemIdByPlu[String(plu)];
        }
        try {
            const response = await fetch(`${resolvePluUrl}?plu=${encodeURIComponent(plu)}`, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
            });
            if (!response.ok) {
                return 0;
            }
            const data = await response.json();
            const itemId = Number(data.item_id || 0);
            if (!itemId) {
                return 0;
            }
            resolvedItemIdByPlu[String(plu)] = itemId;
            return itemId;
        } catch (error) {
            return 0;
        }
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
            const barcodeStats = barcodeStatsByFieldId[field.id];
            const lineTotal = barcodeStats ? Number(barcodeStats.totalPrice || 0) : quantity * price;
            total += lineTotal;
            lines.push({
                field,
                name: tile.dataset.name,
                quantity,
                price,
                barcodeStats,
                touchedAt: itemLastTouchedByFieldId[field.id] || 0,
            });
        });

        if (!lines.length) {
            cartLines.innerHTML = '<p class="empty-state">Tap dishes to build the order.</p>';
            cartTotal.textContent = '0.00';
            return;
        }

        lines.sort((a, b) => b.touchedAt - a.touchedAt);
        cartLines.innerHTML = lines.map((line) => `
            <div class="cart-line">
                <div>
                    <strong>${line.name}</strong>
                    ${line.barcodeStats
                        ? `<span>${line.barcodeStats.totalWeight.toFixed(3)} kg • ${money(line.barcodeStats.totalPrice)} (barcode)</span>`
                        : `<span>${line.quantity} x ${money(line.price)}</span>`}
                </div>
                <div class="qty-controls">
                    <span>${line.barcodeStats ? line.barcodeStats.totalWeight.toFixed(3) : line.quantity}</span>
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
            delete barcodeStatsByFieldId[field.id];
            field.value = Number(field.value || 0) + 1;
            markFieldTouched(field.id);
            updateCart();
        });
    });

    cartLines.addEventListener('click', (event) => {
        const button = event.target.closest('[data-qty-step]');
        if (!button) {
            return;
        }
        const field = document.getElementById(button.dataset.field);
        delete barcodeStatsByFieldId[field.id];
        const nextValue = Math.max(0, Number(field.value || 0) + Number(button.dataset.qtyStep));
        field.value = nextValue;
        markFieldTouched(field.id);
        updateCart();
    });

    clearCartButton.addEventListener('click', () => {
        dishTiles.forEach((tile) => {
            const field = fieldForTile(tile);
            if (field) {
                delete barcodeStatsByFieldId[field.id];
                field.value = 0;
                delete itemLastTouchedByFieldId[field.id];
            }
        });
        updateCart();
    });

    (function registerPluScanListener() {
        const itemIdByPlu = {};
        dishTiles.forEach((tile) => {
            const plu = tile.dataset.plu;
            const field = fieldForTile(tile);
            if (!plu || !field) {
                return;
            }
            const itemId = Number(field.id.replace('id_item_', ''));
            if (itemId) {
                itemIdByPlu[String(plu)] = itemId;
            }
        });

        let scanBuffer = '';
        let lastKeyTime = 0;
        let submitTimer = null;
        let scanInProgress = false;

        async function submitScan() {
            if (scanInProgress) {
                return;
            }
            scanInProgress = true;
            try {
                const parsed = parseScaleBarcode(scanBuffer);
                scanBuffer = '';
                if (!parsed.plu) {
                    return;
                }
                let itemId = itemIdByPlu[String(parsed.plu)];
                if (!itemId) {
                    itemId = await resolveItemIdByPlu(parsed.plu);
                }
                if (!itemId) {
                    return;
                }
                const field = document.getElementById(`id_item_${itemId}`);
                if (!field) {
                    return;
                }
                const tile = Array.from(dishTiles).find((item) => item.dataset.field === field.id);
                const unitPrice = Number(tile ? tile.dataset.price : 0);
                if (!unitPrice || !parsed.barcodePrice) {
                    delete barcodeStatsByFieldId[field.id];
                    field.value = Number(field.value || 0) + 1;
                    markFieldTouched(field.id);
                    updateCart();
                    return;
                }
                const weight = roundWeight(parsed.barcodePrice / unitPrice);
                if (weight <= 0) {
                    return;
                }
                field.value = roundWeight(Number(field.value || 0) + weight);
                const current = barcodeStatsByFieldId[field.id] || { totalWeight: 0, totalPrice: 0 };
                current.totalWeight = roundWeight(current.totalWeight + weight);
                current.totalPrice = Number((current.totalPrice + parsed.barcodePrice).toFixed(2));
                barcodeStatsByFieldId[field.id] = current;
                markFieldTouched(field.id);
                updateCart();
            } finally {
                scanInProgress = false;
            }
        }

        window.addEventListener('keydown', (event) => {
            if (event.ctrlKey || event.altKey || event.metaKey) {
                return;
            }
            const now = Date.now();
            if (event.key === 'Enter') {
                event.preventDefault();
                if (submitTimer) {
                    clearTimeout(submitTimer);
                    submitTimer = null;
                }
                submitScan();
                return;
            }
            if (!/^\d$/.test(event.key)) {
                return;
            }
            if (now - lastKeyTime > 120) {
                scanBuffer = '';
            }
            lastKeyTime = now;
            scanBuffer += event.key;
            if (submitTimer) {
                clearTimeout(submitTimer);
            }
            submitTimer = setTimeout(() => {
                submitScan();
                submitTimer = null;
            }, 140);
            event.preventDefault();
        });
    }());

    activateTab(window.restoSysActiveOrderTab === 'manual' ? 'manual-tab' : 'pos-tab');
    updateCart();
}());
