(function () {
    // Sidebar toggle functionality with state persistence using localStorage
    const body = document.body;
    const button = document.querySelector('.sidebar-toggle');
    const icon = document.querySelector('.sidebar-toggle-icon');
    const storageKey = 'restosys-sidebar-collapsed';

    function applyState(collapsed) {
        body.classList.toggle('sidebar-collapsed', collapsed);
        button.setAttribute('aria-expanded', String(!collapsed));
        icon.textContent = collapsed ? '›' : '‹';
        localStorage.setItem(storageKey, collapsed ? '1' : '0');
    }

    applyState(localStorage.getItem(storageKey) === '1');

    button.addEventListener('click', function () {
        applyState(!body.classList.contains('sidebar-collapsed'));
    });
    // get details of an order
    function getorderdetails(orderId) {
        $.get(`/restaurant/getorderdetails`, { orderid: orderId }, function(data) {
            alert(`Order ID: ${data.id}\nCustomer: ${data.customer_name}\nItems:\n${data.items.map(item => `- ${item.name} x${item.quantity}`).join('\n')}`);
        }).fail(function() {
            alert('Failed to fetch order details. Please try again.');
        });
    }
    
}());
