import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dj_celery.settings")
app = Celery("dj_celery")
# app.config_from_object("dj_celery.settings", namespace="CELERY")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# lambda: settings.INSTALLED_APPS