from celery import shared_task
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

from backend_code.models import Customer
from backend_code.token_gen import generate_token
from django.core.mail import send_mail
from marketplace import settings


@shared_task()
def send_mail_async(subject, body, from_email, to):
    send_mail(subject, body, from_email, to)
