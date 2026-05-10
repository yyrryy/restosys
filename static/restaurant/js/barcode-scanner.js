(function ($) {
    const $form = $('#barcode-scan-form');
    const $barcodeInput = $('#barcode-input');
    const $readyText = $('#scanner-ready-text');
    if (!$form.length || !$barcodeInput.length) {
        return;
    }

    let scanBuffer = '';
    let lastKeyTime = 0;
    let submitTimer = null;

    function setReadyState(text) {
        if ($readyText.length) {
            $readyText.text(text);
        }
    }

    function submitScan() {
        if (scanBuffer.length < 12) {
            return;
        }
        $barcodeInput.val(scanBuffer);
        setReadyState('Processing scan...');
        $form.trigger('submit');
    }

    function queueAutoSubmit() {
        if (submitTimer) {
            clearTimeout(submitTimer);
        }
        submitTimer = setTimeout(submitScan, 140);
    }

    $(window).on('keydown', function (event) {
        if (event.ctrlKey || event.altKey || event.metaKey) {
            return;
        }

        const now = Date.now();
        if (event.key === 'Enter') {
            event.preventDefault();
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
        setReadyState('Scanning...');
        queueAutoSubmit();
        event.preventDefault();
    });
}(jQuery));
