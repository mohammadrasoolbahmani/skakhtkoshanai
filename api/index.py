import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.core.management import call_command
from django.core.wsgi import get_wsgi_application

# Automatically apply migrations and ensure default settings on Vercel Postgres cold starts
if os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL') or os.environ.get('POSTGRES_PRISMA_URL'):
    try:
        call_command('migrate', interactive=False)
        from ailearn.models import CourseSettings
        CourseSettings.get_settings()
    except Exception:
        pass

app = get_wsgi_application()
