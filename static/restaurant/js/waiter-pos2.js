(function ($) {
    const $grid = $('#pos-grid');
    const $cartLines = $('#cart-lines');
    const $cartTotal = $('#cart-total');
    const $clearCartButton = $('#clear-cart');
    const itemMetaById = {};
    const itemIdByPlu = {};
    const barcodeStatsByItemId = {};
    const resolvedItemIdByPlu = {};
    const itemLastTouchedById = {};
    let touchSequence = 0;
    const resolvePluUrl = window.posResolvePluUrl || '';

    if (!$grid.length) {
        return;
    }

    function money(value) {
        return Number(value || 0).toFixed(2);
    }

    function escapeHtml(text) {
        return $('<div>').text(text || '').html();
    }

    function fieldForItem(itemId) {
        return document.getElementById(`id_item_${itemId}`);
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

    function markItemTouched(itemId) {
        touchSequence += 1;
        itemLastTouchedById[itemId] = touchSequence;
    }

    async function resolveItemIdByPlu(plu) {
        if (!plu) {
            return 0;
        }
        if (itemIdByPlu[String(plu)]) {
            return itemIdByPlu[String(plu)];
        }
        if (resolvedItemIdByPlu[String(plu)]) {
            return resolvedItemIdByPlu[String(plu)];
        }
        if (!resolvePluUrl) {
            return 0;
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
            itemIdByPlu[String(plu)] = itemId;
            return itemId;
        } catch (error) {
            return 0;
        }
    }

    function addItemById(itemId) {
        const field = fieldForItem(itemId);
        if (!field) {
            return false;
        }
        field.value = Number(field.value || 0) + 1;
        markItemTouched(itemId);
        updateCart();
        return true;
    }

    function refreshTileSelection() {
        $grid.find('.dish-tile').each(function () {
            const fieldId = this.dataset.field;
            const field = fieldId ? document.getElementById(fieldId) : null;
            const quantity = Number(field ? field.value : 0);
            $(this).toggleClass('selected', quantity > 0);
        });
    }

    function updateCart() {
        const lines = [];
        let total = 0;

        $('input[id^="id_item_"]').each(function () {
            const quantity = Number(this.value || 0);
            if (!quantity) {
                return;
            }

            const itemId = Number(this.id.replace('id_item_', ''));
            if (!itemId) {
                return;
            }

            if (!itemMetaById[itemId]) {
                const $tile = $grid.find(`.dish-tile[data-item-id="${itemId}"]`).first();
                if ($tile.length) {
                    itemMetaById[itemId] = {
                        name: $tile.data('name'),
                        price: Number($tile.data('price') || 0),
                    };
                }
            }

            const item = itemMetaById[itemId] || {
                name: `Item #${itemId}`,
                price: 0,
            };

            const barcodeStats = barcodeStatsByItemId[itemId];
            const lineTotal = barcodeStats ? Number(barcodeStats.totalPrice || 0) : quantity * Number(item.price || 0);
            total += lineTotal;
            lines.push({
                itemId,
                name: item.name,
                quantity,
                price: Number(item.price || 0),
                lineTotal,
                barcodeStats,
                touchedAt: itemLastTouchedById[itemId] || 0,
            });
        });

        refreshTileSelection();

        if (!lines.length) {
            $cartLines.html('<p class="empty-state">Tap dishes to build the order.</p>');
            $cartTotal.text('0.00');
            return;
        }

        lines.sort((a, b) => b.touchedAt - a.touchedAt || b.itemId - a.itemId);

        const linesHtml = lines.map((line) => `
            <div class="cart-line">
                <div>
                    <strong>${escapeHtml(line.name)}</strong>
                    ${line.barcodeStats
                        ? `<span>${line.barcodeStats.totalWeight.toFixed(3)} kg • ${money(line.barcodeStats.totalPrice)}Dh (barcode)</span>`
                        : `<span>${line.quantity} x ${money(line.price)}</span>`}
                </div>
                <div class="qty-controls">
                    ${line.barcodeStats
                        ?
                    `
                    <span>${line.barcodeStats ? line.barcodeStats.totalWeight.toFixed(3) : line.quantity}</span>
                    `
                    :
                    `<button type="button" data-qty-step="-1" data-item-id="${line.itemId}">-</button>
                    <span>${line.barcodeStats ? line.barcodeStats.totalWeight.toFixed(3) : line.quantity}</span>
                    <button type="button" data-qty-step="1" data-item-id="${line.itemId}">+</button>`}
                </div>
            </div>
        `).join('');
        $cartLines.html(linesHtml);
        $cartTotal.text(money(total));
    }

    function renderItems(items) {
        if (!items.length) {
            $grid.html('<p class="empty-state">No available dishes in this category.</p>');
            return;
        }

        const $fragment = $(document.createDocumentFragment());
        items.forEach((item) => {
            itemMetaById[item.id] = {
                name: item.name,
                price: Number(item.price || 0),
            };

            const $tile = $('<button>', {
                class: 'dish-tile',
                type: 'button',
            });
            $tile.attr('data-category', item.category);
            $tile.attr('data-field', `id_item_${item.id}`);
            $tile.attr('data-item-id', item.id);
            $tile.attr('data-name', item.name);
            $tile.attr('data-price', item.price);
            if (item.plu !== null && item.plu !== undefined && item.plu !== '') {
                $tile.attr('data-plu', item.plu);
                itemIdByPlu[String(item.plu)] = item.id;
            }
            $tile.append($('<img>', { src: item.display_image, alt: item.name }));
            $tile.append($('<strong>').text(item.name));
            $tile.append($('<span>').text(item.category));
            $tile.append($('<small>').text(money(item.price)));
            $fragment.append($tile);
        });

        $grid.empty().append($fragment);
    }

    function loadCategoryItems(category) {
        const itemsUrl = $grid.data('items-url');
        if (!itemsUrl) {
            return;
        }

        $grid.html('<p class="empty-state">Loading...</p>');
        $.ajax({
            url: itemsUrl,
            method: 'GET',
            dataType: 'json',
            data: { category: category },
            success: function (response) {
                renderItems(response.items || []);
                updateCart();
            },
            error: function () {
                $grid.html('<p class="empty-state">Could not load products for this category.</p>');
            },
        });
    }

    $(document).on('click', '.category-chip', function () {
        const $button = $(this);
        $('.category-chip').removeClass('active');
        $button.addClass('active');
        loadCategoryItems($button.data('category'));
    });

    $grid.on('click', '.dish-tile', function () {
        const itemId = Number(this.dataset.itemId);
        delete barcodeStatsByItemId[itemId];
        addItemById(itemId);
    });

    $cartLines.on('click', '[data-qty-step]', function () {
        const step = Number(this.dataset.qtyStep || 0);
        const itemId = Number(this.dataset.itemId || 0);
        const field = fieldForItem(itemId);
        if (!field) {
            return;
        }
        delete barcodeStatsByItemId[itemId];
        markItemTouched(itemId);
        field.value = Math.max(0, Number(field.value || 0) + step);
        updateCart();
    });

    $clearCartButton.on('click', function () {
        $('input[id^="id_item_"]').val(0);
        Object.keys(barcodeStatsByItemId).forEach(function (key) {
            delete barcodeStatsByItemId[key];
        });
        Object.keys(itemLastTouchedById).forEach(function (key) {
            delete itemLastTouchedById[key];
        });
        updateCart();
    });

    (function registerPluScanListener() {
        const payloadScript = document.getElementById('pos2-items-payload');
        if (payloadScript) {
            try {
                const allItems = JSON.parse(payloadScript.textContent || '[]');
                allItems.forEach(function (item) {
                    itemMetaById[item.id] = {
                        name: item.name,
                        price: Number(item.price || 0),
                    };
                    if (item.plu !== null && item.plu !== undefined && item.plu !== '') {
                        itemIdByPlu[String(item.plu)] = item.id;
                    }
                });
            } catch (error) {
                // ignore malformed payload
            }
        }

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
                const item = itemMetaById[itemId];
                if (!item) {
                    return;
                }
                const unitPrice = Number(item.price || 0);
                if (!unitPrice || !parsed.barcodePrice) {
                    delete barcodeStatsByItemId[itemId];
                    addItemById(itemId);
                    return;
                }
                const weight = roundWeight(parsed.barcodePrice / unitPrice);
                if (weight <= 0) {
                    return;
                }
                const field = fieldForItem(itemId);
                if (!field) {
                    return;
                }
                field.value = roundWeight(Number(field.value || 0) + weight);
                const current = barcodeStatsByItemId[itemId] || { totalWeight: 0, totalPrice: 0 };
                current.totalWeight = roundWeight(current.totalWeight + weight);
                current.totalPrice = Number((current.totalPrice + parsed.barcodePrice).toFixed(2));
                barcodeStatsByItemId[itemId] = current;
                markItemTouched(itemId);
                updateCart();
            } finally {
                scanInProgress = false;
            }
        }

        $(window).on('keydown', function (event) {
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
            submitTimer = setTimeout(function () {
                submitScan();
                submitTimer = null;
            }, 140);
            event.preventDefault();
        });
    }());

    updateCart();
}(window.jQuery));
