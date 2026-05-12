from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Order
from .printing import dispatch_payment_receipt


@receiver(pre_save, sender=Order)
def capture_previous_order_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_status = None
        return
    instance._previous_status = (
        Order.objects.filter(pk=instance.pk).values_list('status', flat=True).first()
    )


@receiver(post_save, sender=Order)
def print_payment_receipt_when_order_paid(sender, instance, created, **kwargs):
    previous_status = getattr(instance, '_previous_status', None)
    became_paid = instance.status == Order.STATUS_PAID and (created or previous_status != Order.STATUS_PAID)
    if became_paid:
        dispatch_payment_receipt(instance.pk)
