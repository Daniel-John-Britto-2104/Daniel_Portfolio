"""
WSGI config for portfolio project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'portfolio.settings')

# Automatic static collection fallback on Render if build command skipped collectstatic
try:
    from django.conf import settings
    static_root = Path(settings.STATIC_ROOT)
    if not static_root.exists() or not any(static_root.iterdir()):
        import django
        django.setup()
        from django.core.management import call_command
        call_command('collectstatic', interactive=False, verbosity=0)
except Exception:
    pass

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
