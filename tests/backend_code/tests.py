import pytest
from django.contrib.auth.hashers import make_password
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from backend_code.models import Customer, Product, Store, StoreCategory, ProductCategory, Basket
from marketplace import settings


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def sample_user():
    sample_user = Customer.objects.create(**{'first_name': '1', 'last_name': '1', 'email_login': settings.EMAIL_TO_USER, 'password': make_password('valid0_password'), 'user_name': '1', 'phone_number': '1', 'area_code': '1', 'registered_vendor': True, 'is_active': True})
    sample_user.email_verified = True
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
    sample_store.cats.add(sample_store_cat.id)
    sample_store.save()
    return sample_store


@pytest.fixture
def sample_product_cat(login_user):
    sample_product_cat = ProductCategory.objects.create(prod_cat_id=1, name='name')
    return sample_product_cat


@pytest.fixture
def sample_product(sample_store, sample_product_cat):
    sample_product = Product.objects.create(stock_number=15, name='name', amount=5, price=100, weight_class=1, recommended_price=50, delivery_store=sample_store, product_cat=sample_product_cat)
    return sample_product


@pytest.fixture
def sample_basket(login_user, sample_product, sample_store):
    sample_basket = Basket.objects.create(b_customer=login_user, b_product=sample_product, b_vendor=sample_store, amount=100)
    return sample_basket


class TestUser:

    # user signup
    @pytest.mark.parametrize('user_email', ['error', settings.EMAIL_TO_USER])
    @pytest.mark.parametrize('password', ['short', 'valid0_password'])
    @pytest.mark.django_db(transaction=True)
    def test_user_signup(self, client, user_email, password):
        sample_user = {'first_name': '1', 'last_name': '1', 'email_login': user_email, 'password': password, 'user_name': '1', 'phone_number': '1', 'area_code': '1', 'registered_vendor': True, 'is_active': True}
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
    @pytest.mark.parametrize('email_login_check', ['no_user@none.com', settings.EMAIL_TO_USER])
    @pytest.mark.django_db(transaction=True)
    def test_user_view(self, client, login_user, email_login_check):
        response_user_view = client.get(reverse('backend_code:customer-set'), data={'email_login': email_login_check})
        assert response_user_view.status_code == 200

    # user edit
    @pytest.mark.parametrize('patch_user_email', ['no_user@none.com', settings.EMAIL_TO_USER])
    @pytest.mark.parametrize('password_change', ['short', 'new_valid0_password'])
    @pytest.mark.parametrize('registered_vendor_change', ['no_value', False])
    @pytest.mark.django_db(transaction=True)
    def test_user_patch(self, client, login_user, patch_user_email, password_change, registered_vendor_change):
        response_user_patch = client.patch('/api/v1/customers/', data = {'email_login': patch_user_email, 'password': password_change, 'registered_vendor': registered_vendor_change})
        assert response_user_patch.status_code == 200

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


class TestStore:

    # store create
    @pytest.mark.parametrize('store_create_user', ['no_user@none.com', settings.EMAIL_TO_USER])
    @pytest.mark.parametrize('store_create_price', ['chars', 50])
    @pytest.mark.django_db(transaction=True)
    def test_store_create(self, client, sample_store_cat, store_create_user, store_create_price):
        response_store_create = client.post('/api/v1/store/', data={'email_login': store_create_user, 'name': 'name', 'address': 'address', 'nominal_delivery_price': store_create_price, 'store_cat_id': sample_store_cat.store_cat_id})
        assert response_store_create.status_code == 200

    # store delete
    @pytest.mark.parametrize('store_delete_user', ['no_user@none.com', settings.EMAIL_TO_USER])
    @pytest.mark.django_db(transaction=True)
    def test_store_delete(self, client, sample_store, store_delete_user):
        response_store_delete = client.delete('/api/v1/store/', data={'email_login': store_delete_user})
        assert response_store_delete.status_code == 204


    # store view
    @pytest.mark.parametrize('store_view_user', ['no_user@none.com', settings.EMAIL_TO_USER])
    @pytest.mark.django_db(transaction=True)
    def test_store_view(self, client, sample_store, store_view_user):
        response_store_view = client.get(reverse('backend_code:store-set'), data={'email_login': store_view_user})
        assert response_store_view.status_code == 200

    # store update
    @pytest.mark.parametrize('store_update_user', ['no_user@none.com', settings.EMAIL_TO_USER])
    @pytest.mark.parametrize('store_update_price', ['chars', 50])
    @pytest.mark.django_db(transaction=True)
    def test_store_update(self, client, sample_store, store_update_user, store_update_price):
        response_store_update = client.patch('/api/v1/store/', data={'email_login': store_update_user, 'nominal_delivery_price': store_update_price})
        assert response_store_update.status_code == 200


class TestBasket:

    # basket create/update
    @pytest.mark.parametrize('basket_create_user', ['no_user@none.com', settings.EMAIL_TO_USER])
    @pytest.mark.parametrize('basket_create_stock_number', ['chars', 500, 15])
    @pytest.mark.django_db(transaction=True)
    def test_basket_create(self, client, sample_product, basket_create_user, basket_create_stock_number):
        response_basket_create = client.post('/api/v1/basket/', data={'email_login': basket_create_user, 'stock_number': basket_create_stock_number, 'amount': 100})
        assert response_basket_create.status_code == 200

    # basket view
    @pytest.mark.parametrize('basket_view_user', ['no_user@none.com', settings.EMAIL_TO_USER])
    @pytest.mark.django_db(transaction=True)
    def test_basket_view(self, client, sample_basket, basket_view_user):
        response_basket_view = client.get('/api/v1/basket/', data={'email_login': basket_view_user})
        assert response_basket_view.status_code == 200

    # basket delete
    @pytest.mark.parametrize('basket_delete_user', ['no_user@none.com', settings.EMAIL_TO_USER])
    @pytest.mark.parametrize('basket_delete_stock_number', ['chars', 500, 15])
    @pytest.mark.django_db(transaction=True)
    def test_basket_delete(self, client, sample_basket, basket_delete_user, basket_delete_stock_number):
        response_basket_delete = client.delete('/api/v1/basket/', data={'email_login': basket_delete_user, 'stock_number': basket_delete_stock_number})
        assert response_basket_delete.status_code == 204


class TestStoreCat:

    # store cat create/update
    @pytest.mark.parametrize('stc_create_user', ['no_user@none.com', settings.EMAIL_TO_USER])
    @pytest.mark.parametrize('stc_create_name', [None, 'name'])
    @pytest.mark.django_db(transaction=True)
    def test_stc_create(self, client, login_user, stc_create_user, stc_create_name):
        response_stc_create = client.post('/api/v1/store-cat/', data={'email_login': stc_create_user, 'name': stc_create_name})
        assert response_stc_create.status_code == 200


    # store cat view
    @pytest.mark.parametrize('stc_view_user', ['no_user@none.com', settings.EMAIL_TO_USER])
    @pytest.mark.parametrize('stc_view_id', [None, 100, 1])
    @pytest.mark.django_db(transaction=True)
    def test_stc_view(self, client, sample_store_cat, stc_view_user, stc_view_id):
        response_stc_view = client.get('/api/v1/store-cat/', data={'email_login': stc_view_user, 'store_cat_id': stc_view_id})
        assert response_stc_view.status_code == 200

    # store cat delete
    @pytest.mark.parametrize('stc_delete_user', ['no_user@none.com', settings.EMAIL_TO_USER])
    @pytest.mark.parametrize('stc_delete_id', [100, 1])
    @pytest.mark.django_db(transaction=True)
    def test_stc_delete(self, client, sample_store_cat, stc_delete_user, stc_delete_id):
        response_stc_delete = client.delete('/api/v1/store-cat/', data={'email_login': stc_delete_user, 'store_cat_id': stc_delete_id})
        assert response_stc_delete.status_code == 204

    # store cat delete with existing stores
    @pytest.mark.django_db(transaction=True)
    def test_stc_delete_not_empty(self, client, sample_store):
        response_stc_delete_not_empty = client.delete('/api/v1/store-cat/', data={'email_login': settings.EMAIL_TO_USER, 'store_cat_id': 1})
        assert response_stc_delete_not_empty.status_code == 406


class TestProductCat:

    # product category create/update
    @pytest.mark.parametrize('pc_create_user', ['no_user@none.com', settings.EMAIL_TO_USER])
    @pytest.mark.parametrize('pc_create_name', [None, 'name'])
    @pytest.mark.django_db(transaction=True)
    def test_pc_create(self, client, login_user, pc_create_user, pc_create_name):
        response_pc_create = client.post('/api/v1/prod-cat/', data={'email_login': pc_create_user, 'name': pc_create_name})
        assert response_pc_create.status_code == 200

    # product category view
    @pytest.mark.parametrize('pc_view_id', [None, 100, 1])
    @pytest.mark.django_db(transaction=True)
    def test_pc_view(self, client, sample_product_cat, pc_view_id):
        response_pc_view = client.get('/api/v1/prod-cat/', data={'prod_cat_id': pc_view_id})
        assert response_pc_view.status_code == 200
