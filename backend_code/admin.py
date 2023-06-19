from django.contrib import admin
from django.contrib.auth.models import PermissionsMixin
from django.contrib.auth.admin import UserAdmin
from .models import Customer


class CustomerAdmin(admin.ModelAdmin):
    list_display = ['email_login', 'user_name']

admin.site.register(Customer, CustomerAdmin)
