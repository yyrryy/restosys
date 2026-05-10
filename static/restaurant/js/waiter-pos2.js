(function ($) {
    const $grid = $('#pos-grid');
    const $cartLines = $('#cart-lines');
    const $cartTotal = $('#cart-total');
    const $clearCartButton = $('#clear-cart');
    const itemMetaById = {};

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

            total += quantity * Number(item.price || 0);
            lines.push({
                itemId,
                name: item.name,
                quantity,
                price: Number(item.price || 0),
            });
        });

        refreshTileSelection();

        if (!lines.length) {
            $cartLines.html('<p class="empty-state">Tap dishes to build the order.</p>');
            $cartTotal.text('0.00');
            return;
        }

        const linesHtml = lines.map((line) => `
            <div class="cart-line">
                <div>
                    <strong>${escapeHtml(line.name)}</strong>
                    <span>${line.quantity} x ${money(line.price)}</span>
                </div>
                <div class="qty-controls">
                    <button type="button" data-qty-step="-1" data-item-id="${line.itemId}">-</button>
                    <span>${line.quantity}</span>
                    <button type="button" data-qty-step="1" data-item-id="${line.itemId}">+</button>
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
        const field = fieldForItem(itemId);
        if (!field) {
            return;
        }
        field.value = Number(field.value || 0) + 1;
        updateCart();
    });

    $cartLines.on('click', '[data-qty-step]', function () {
        const step = Number(this.dataset.qtyStep || 0);
        const itemId = Number(this.dataset.itemId || 0);
        const field = fieldForItem(itemId);
        if (!field) {
            return;
        }
        field.value = Math.max(0, Number(field.value || 0) + step);
        updateCart();
    });

    $clearCartButton.on('click', function () {
        $('input[id^="id_item_"]').val(0);
        updateCart();
    });

    updateCart();
}(window.jQuery));
