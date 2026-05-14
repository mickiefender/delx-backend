"""
Django management command to create an admin user.
"""
from django.core.management.base import BaseCommand
from users.models import CustomUser


class Command(BaseCommand):
    help = 'Creates an admin superuser account'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='admin',
            help='Username for the admin user',
        )
        parser.add_argument(
            '--email',
            type=str,
            default='admin@delchris.com',
            help='Email for the admin user',
        )
        parser.add_argument(
            '--password',
            type=str,
            default='admin123',
            help='Password for the admin user',
        )

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']

        if CustomUser.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f'User "{username}" already exists.')
            )
            # Update the existing user to be admin
            user = CustomUser.objects.get(username=username)
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.set_password(password)
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f'Updated user "{username}" to be admin.')
            )
        else:
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=password,
                is_staff=True,
                is_superuser=True,
                is_active=True,
            )
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created admin user: {username}')
            )
        
        self.stdout.write(self.style.SUCCESS(f'Admin login credentials:'))
        self.stdout.write(f'  Username: {username}')
        self.stdout.write(f'  Password: {password}')
