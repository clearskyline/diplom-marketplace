from allauth.account.adapter import DefaultAccountAdapter
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token


class CustomAdapter(DefaultAccountAdapter):

    # Google authentication can be disabled here
    def is_open_for_signup(self, request):
        return True

    # add extra fields to Customer object
    def populate_username(self, request, user):
        super(CustomAdapter, self).populate_username(request, user)
        user.email_verified = True
        user.user_name = user.first_name
        user.save()

    # login user with custom token
    def login(self, request, user):
        super(CustomAdapter, self).login(request, user)
        token_ = Token.objects.filter(user=user).first()
        if token_:
            token_.delete()
        token = Token.objects.create(user=user)
