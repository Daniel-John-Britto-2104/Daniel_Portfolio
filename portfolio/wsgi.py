"""
WSGI config for portfolio project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'portfolio.settings')

# Automatic static collection and database migration fallback on Render
try:
    import django
    django.setup()
    from django.conf import settings
    from django.core.management import call_command

    static_root = Path(settings.STATIC_ROOT)
    if not static_root.exists() or not any(static_root.iterdir()):
        call_command('collectstatic', interactive=False, verbosity=0)

    # Automatically ensure database tables/migrations are up to date
    call_command('migrate', interactive=False, verbosity=0)
except Exception:
    pass

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
