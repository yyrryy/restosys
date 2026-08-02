from .models import Orderfromserver, Orderitemfromserver
# create orders that will come from the server
def createorders(orders):
    print(f"Creating {len(orders)} orders...", orders)
    for o in orders:
        # 1. Create order
        order = Orderfromserver.objects.create(
            date=o['date'],
            total=o['total'],
            note=o['note'],
            clientname=o['clientname'],
            clientaddress=o['clientaddress'],
            clientphone=o['clientphone'],
            order_no=o['order_no'],
        )

        items = o['items']
        order_items = [
            Orderitemfromserver(
                order=order,
                name=item['name'],
                qty=item['qty'],
                price=item['price'],
                total=item['total'],
            )
            for item in items
        ]

        # 5. Bulk insert
        Orderitemfromserver.objects.bulk_create(order_items)