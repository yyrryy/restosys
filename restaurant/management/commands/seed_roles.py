from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from restaurant.models import UserProfile


class Command(BaseCommand):
    help = 'Create the starter RestoSys accounts.'

    def handle(self, *args, **options):
        password = 'restosys123'
        accounts = [
            ('owner', UserProfile.ROLE_OWNER, True),
            ('admin', UserProfile.ROLE_ADMIN, False),
            ('waiter', UserProfile.ROLE_WAITER, False),
            ('kitchen', UserProfile.ROLE_KITCHEN, False),
            ('cashier', UserProfile.ROLE_CASHIER, False),
        ]

        for username, role, is_staff in accounts:
            user, created = User.objects.get_or_create(username=username)
            user.is_staff = is_staff
            user.is_superuser = role == UserProfile.ROLE_OWNER
            user.set_password(password)
            user.save()
            UserProfile.objects.update_or_create(user=user, defaults={'role': role})
            action = 'Created' if created else 'Updated'
            self.stdout.write(f'{action} {username} / {password}')
