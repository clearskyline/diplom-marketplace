import pytest
from django.contrib.auth.hashers import make_password
from rest_framework.test import APIClient

from backend_code.models import Customer
from marketplace import settings


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def sample_user():
    sample_user = Customer.objects.create(**{'first_name': '1', 'last_name': '1', 'email_login': settings.EMAIL_TO_USER, 'password': make_password('valid0_password'), 'user_name': '1', 'phone_number': '1', 'area_code': '1', 'registered_vendor': '1', 'is_active': '1'})
    return sample_user


class TestUser:

    # user signup
    @pytest.mark.parametrize('user_email', ['error', settings.EMAIL_TO_USER])
    @pytest.mark.parametrize('password', ['short', 'valid0_password'])
    @pytest.mark.django_db(transaction=True)
    def test_user_signup(self, client, user_email, password):
        sample_user = {'first_name': '1', 'last_name': '1', 'email_login': user_email, 'password': password, 'user_name': '1', 'phone_number': '1', 'area_code': '1', 'registered_vendor': '1', 'is_active': '1'}
        response_signup = client.post('/api/v1/user-signup/', data=sample_user)
        assert response_signup.status_code == 201

    # user login
    @pytest.mark.parametrize('email_verified_check', [False, True])
    @pytest.mark.django_db(transaction=True)
    def test_login(self, client, sample_user, email_verified_check):
        sample_user.email_verified = email_verified_check
        sample_user.save()
        response_login = client.post('/api/v1/login/', data={'email_login': sample_user.email_login, 'password': 'valid0_password'})
        assert response_login.status_code == 200
