from allauth.account.adapter import DefaultAccountAdapter
from rest_framework.authtoken.models import Token


class CustomAdapter(DefaultAccountAdapter):

    def save_user(self, request, user, form, commit=True):

        user = super(CustomAdapter, self).save_user(request, user, form, commit=True)
        token_ = Token.objects.filter(user=user).first()
        if token_:
            token_.delete()
        token = Token.objects.create(user=user)
        return user
