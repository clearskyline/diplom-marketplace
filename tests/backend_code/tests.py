import pytest
from django.contrib.auth.hashers import make_password
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from backend_code.models import Customer, Product, Store, StoreCategory, ProductCategory
from marketplace import settings


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def sample_user():
    sample_user = Customer.objects.create(**{'first_name': '1', 'last_name': '1', 'email_login': settings.EMAIL_TO_USER, 'password': make_password('valid0_password'), 'user_name': '1', 'phone_number': '1', 'area_code': '1', 'registered_vendor': '1', 'is_active': '1'})
    return sample_user


@pytest.fixture
def login_user(sample_user):
    Token.objects.create(user=sample_user)
    login_user = sample_user
    return login_user


@pytest.fixture
def sample_store_cat(login_user):
    sample_store_cat = StoreCategory.objects.create(store_cat_id=1, store_cat_creator=login_user, name='name')
    return sample_store_cat

@pytest.fixture
def sample_store(login_user, sample_store_cat):
    sample_store = Store.objects.create(vendor_id=login_user, name='name', address='address', nominal_delivery_price=50, status=True)
    return sample_store


@pytest.fixture
def sample_product_cat(login_user):
    sample_product_cat = ProductCategory.objects.create(prod_cat_id=1, name='name')
    return sample_product_cat


@pytest.fixture
def sample_product(sample_store, sample_product_cat):
    sample_product = Product.objects.create(stock_number=15, name='name', amount=5, price=100, weight_class=1, recommended_price=50, delivery_store=sample_store, product_cat=sample_product_cat)
    return sample_product


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
    @pytest.mark.parametrize('password_check', ['incorrect_password', 'valid0_password'])
    @pytest.mark.django_db(transaction=True)
    def test_login(self, client, sample_user, email_verified_check, password_check):
        sample_user.email_verified = email_verified_check
        sample_user.save()
        response_login = client.post('/api/v1/login/', data={'email_login': sample_user.email_login, 'password': password_check})
        assert response_login.status_code == 200

    # user view
    # @pytest.mark.parametrize('email_login_check', ['error', settings.EMAIL_TO_USER])
    @pytest.mark.django_db(transaction=True)
    def test_user_view(self, client, login_user):
        response_user_view = client.get('/api/v1/customers/', data={'email_login': login_user.email_login})
        assert response_user_view.json() == 200

    # user edit
    @pytest.mark.parametrize('password_change', ['short', 'new_valid0_password'])
    @pytest.mark.django_db(transaction=True)
    def test_user_patch(self, client, login_user, password_change):
        response_user_patch = client.patch('/api/v1/customers/', data = {'password': password_change})
        assert response_user_patch.json() == 200

    # user delete
    @pytest.mark.parametrize('delete_user', ['no_user@none.com', settings.EMAIL_TO_USER])
    @pytest.mark.django_db(transaction=True)
    def test_user_delete(self, client, login_user, delete_user):
        response_user_delete = client.delete('/api/v1/customers/', data={'email_login': delete_user})
        assert response_user_delete.status_code == 204


class TestProduct:

    # get product by slug (stock number)
    @pytest.mark.parametrize('stock_number_check', [1, 15])
    @pytest.mark.django_db(transaction=True)
    def test_get_product(self, client, sample_product, stock_number_check):
        response_get_product = client.get(f'/api/v1/goods/{stock_number_check}/')
        assert response_get_product.status_code == 200

    # search product by name/model
    @pytest.mark.parametrize('search_keyword', ['unused_keyword', 'n'])
    @pytest.mark.django_db(transaction=True)
    def test_search_product(self, client, sample_product, search_keyword):
        response_search_product = client.get(f'/api/v1/goods/?s={search_keyword}')
        assert response_search_product.json()['count'] > 0

    # delete product (with auth)
    @pytest.mark.parametrize('stock_number_check', [1, 15])
    @pytest.mark.django_db(transaction=True)
    def test_delete_product(self, client, sample_product, stock_number_check):
        response_delete_product = client.get(f'/api/v1/goods/{stock_number_check}/')
        assert response_delete_product.status_code == 200
