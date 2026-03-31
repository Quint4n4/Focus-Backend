"""
ASGI config for Focus project.

Expone el callable ASGI como una variable de módulo llamada ``application``.
Referencia: https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

application = get_asgi_application()
