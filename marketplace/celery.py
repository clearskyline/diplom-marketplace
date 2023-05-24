import os
from celery import Celery

from marketplace import settings


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "marketplace.settings")
app = Celery("marketplace")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
