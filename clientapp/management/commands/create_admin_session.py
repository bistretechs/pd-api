from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.contrib.auth import get_user_model
from importlib import import_module
from django.conf import settings

class Command(BaseCommand):
    help = 'Create an authenticated session for admin access'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='superadmin',
            help='Username to create session for'
        )

    def handle(self, *args, **options):
        username = options['username']
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User "{username}" does not exist'))
            return

        if not user.is_active or not user.is_staff:
            self.stdout.write(self.style.ERROR(f'User "{username}" must be active and staff'))
            return

        engine = import_module(settings.SESSION_ENGINE)
        session = engine.SessionStore()
        session['_auth_user_id'] = str(user.pk)
        session['_auth_user_backend'] = 'django.contrib.auth.backends.ModelBackend'
        session['_auth_user_hash'] = user.get_session_auth_hash()
        session.save()

        self.stdout.write(self.style.SUCCESS('\n✅ Session created successfully!\n'))
        self.stdout.write(self.style.WARNING('Copy this session key:\n'))
        self.stdout.write(f'{session.session_key}\n')
        self.stdout.write(self.style.WARNING('\nInstructions:'))
        self.stdout.write('1. Open http://localhost:8000/admin/ in your browser')
        self.stdout.write('2. Press F12 to open DevTools')
        self.stdout.write('3. Go to Application/Storage > Cookies > http://localhost:8000')
        self.stdout.write('4. Add a new cookie:')
        self.stdout.write('   Name: sessionid')
        self.stdout.write(f'   Value: {session.session_key}')
        self.stdout.write('   Domain: localhost')
        self.stdout.write('   Path: /')
        self.stdout.write('   HttpOnly: ✓')
        self.stdout.write('5. Refresh the page - you should be logged in!\n')
