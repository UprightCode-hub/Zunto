
from django.core.management.base import BaseCommand
from django.db import connection
from django.core.cache import cache
import sys


class Command(BaseCommand):
    help = 'Check system health and configuration'
    
    def handle(self, *args, **options):
        checks = [
            self.check_database,
            self.check_cache,
            self.check_email,
            self.check_celery,
            self.check_static_files,
        ]
        
        all_passed = True
        
        for check in checks:
            if not check():
                all_passed = False
        
        if all_passed:
            self.stdout.write(
                self.style.SUCCESS('\n✓ All system checks passed!')
            )
        else:
            self.stdout.write(
                self.style.ERROR('\n✗ Some system checks failed!')
            )
            sys.exit(1)
    
    def check_database(self):
        self.stdout.write('Checking database connection... ', ending='')
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            self.stdout.write(self.style.SUCCESS('✓'))
            return True
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ {str(e)}'))
            return False
    
    def check_cache(self):
        self.stdout.write('Checking cache... ', ending='')
        try:
            cache.set('test_key', 'test_value', 10)
            if cache.get('test_key') == 'test_value':
                self.stdout.write(self.style.SUCCESS('✓'))
                return True
            else:
                raise Exception('Cache read/write failed')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ {str(e)}'))
            return False
    
    def check_email(self):
        self.stdout.write('Checking email configuration... ', ending='')
        from django.conf import settings
        
        if not settings.EMAIL_HOST_USER:
            self.stdout.write(self.style.WARNING('⚠ EMAIL_HOST_USER not configured'))
            return False
        
        self.stdout.write(self.style.SUCCESS('✓'))
        return True
    
    def check_celery(self):
        self.stdout.write('Checking Celery workers... ', ending='')
        try:
            from zonto_config.celery import app
            inspect = app.control.inspect()
            active = inspect.active()
            
            if active:
                self.stdout.write(self.style.SUCCESS('✓'))
                return True
            else:
                self.stdout.write(self.style.WARNING('⚠ No active workers'))
                return False
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ {str(e)}'))
            return False
    
    def check_static_files(self):
        self.stdout.write('Checking static files... ', ending='')
        from django.conf import settings
        import os
        
        if not os.path.exists(settings.STATIC_ROOT):
            self.stdout.write(self.style.WARNING('⚠ Run collectstatic'))
            return False
        
        self.stdout.write(self.style.SUCCESS('✓'))
        return True