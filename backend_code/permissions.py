from rest_framework.permissions import BasePermission
from rest_framework.authtoken.models import Token
from datetime import datetime, timedelta
from backend_code.models import Customer


class IsLoggedIn(BasePermission):

    def has_permission(self, request, view):
        if {'email_login'}.issubset(request.data):
            current_customer = Customer.objects.filter(email_login=request.data['email_login']).first()
            if current_customer:
                token = Token.objects.filter(user=current_customer).first()
                if token:
                    return token.created > datetime.now() - timedelta(hours=1)
        return False


class IsProductOwner(BasePermission):

    def has_object_permission(self, request, view, obj):
        return obj.delivery_store.vendor_id.email_login == request.data['email_login']


class IsStoreCatOwner(BasePermission):

    def has_object_permission(self, request, view, obj):
        return obj.store_cat_creator.email_login == request.data['email_login']

