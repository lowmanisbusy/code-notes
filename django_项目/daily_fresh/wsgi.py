"""
WSGI config for daily_fresh project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/howto/deployment/wsgi/
"""

import os

# django 遵循wsgi协议,在这里导入wsgi接口
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "daily_fresh.settings")

application = get_wsgi_application()
