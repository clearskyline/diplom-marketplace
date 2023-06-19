from allauth.account.adapter import DefaultAccountAdapter
from rest_framework.authtoken.models import Token


class CustomAdapter(DefaultAccountAdapter):

    def is_open_for_signup(self, request):
        return True

    def populate_username(self, request, user):
        super(CustomAdapter, self).populate_username(request, user)
        user.email_verified = True
        user.user_name = user.first_name
        user.save()
        token_ = Token.objects.filter(user=user).first()
        if token_:
            token_.delete()
        token = Token.objects.create(user=user)
