"""
WSGI config for Focus project.

Expone el callable WSGI como una variable de módulo llamada ``application``.
Gunicorn lo usa con: gunicorn config.wsgi:application
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

application = get_wsgi_application()
