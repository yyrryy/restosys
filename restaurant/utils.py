from django.db import transaction

from .models import Orderfromserver, Orderitemfromserver


# create orders that will come from the server
def createorders(orders):
    created = 0
    for o in orders:
        order_no = o.get('order_no')
        if order_no and Orderfromserver.objects.filter(order_no=order_no).exists():
            continue

        with transaction.atomic():
            order = Orderfromserver.objects.create(
                date=o['date'],
                total=o['total'],
                deliveryfees=o['deliveryfees'],
                note=o['note'],
                clientname=o['clientname'],
                clientaddress=o['clientaddress'],
                clientphone=o['clientphone'],
                order_no=order_no,
            )

            order_items = [
                Orderitemfromserver(
                    order=order,
                    name=item['name'],
                    qty=item['qty'],
                    price=item['price'],
                    total=item['total'],
                )
                for item in o['items']
            ]

            Orderitemfromserver.objects.bulk_create(order_items)
        created += 1

    return created