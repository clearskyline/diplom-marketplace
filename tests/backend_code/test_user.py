import pytest
from rest_framework.test import APIClient

from marketplace import settings


@pytest.fixture
def client():
    return APIClient()


# user signup
@pytest.mark.parametrize('user_email', ['error', settings.EMAIL_TO_USER])
@pytest.mark.parametrize('password', ['short', 'valid0_password'])
@pytest.mark.django_db()
def test_user_signup(client, user_email, password):
    sample_user = {'first_name': '1', 'last_name': '1', 'email_login': user_email, 'password': password, 'user_name': '1', 'phone_number': '1', 'area_code': '1', 'registered_vendor': '1', 'is_active': '1'}
    response = client.post('/api/v1/user-signup/', data=sample_user)
    assert response.status_code == 201





