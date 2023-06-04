import json
import random
import threading

import requests.utils
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.password_validation import validate_password
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMessage
from django.core.serializers import get_serializer
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Q
from django.forms import forms
from django.template.loader import render_to_string
from django.utils.datastructures import MultiValueDictKeyError
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from rest_framework import viewsets
from rest_framework.authtoken.models import Token
from django.http import JsonResponse
from django.shortcuts import render, redirect
from rest_framework.decorators import action, permission_classes, api_view
from rest_framework.generics import RetrieveDestroyAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from datetime import datetime, timedelta
import yaml
from rest_framework.viewsets import ViewSet

from backend_code.models import Product, ProductCategory, Store, Customer, Basket, ProductParameters, StoreCategory, \
    Order
from backend_code.permissions import IsLoggedIn
from backend_code.serializers import ProductSerializer, CustomerSerializer, StoreSerializer, BasketSerializer, \
    StoreCatSerializer, ProdCatSerializer, OrderSerializer, OrderItemSerializer
from backend_code.token_gen import generate_token

from backend_code.tasks import send_mail_async, import_product_list_async, export_product_list_async


def send_activation_email(user, request):
    current_site = get_current_site(request)
    email_subject = "Activation email"
    email_body = render_to_string('authentication/activate.html', {
        'user': user,
        'domain': current_site,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': generate_token.make_token(user)
    })

    send_mail_async.delay(email_subject, email_body, settings.EMAIL_FROM_USER, [user.email_login])


def activate_user(request, uidb64, token):

    try:
        uid=force_text(urlsafe_base64_decode(uidb64))

        user = Customer.objects.get(pk=uid)

    except Exception as err:
        user=None

    if user and generate_token.check_token(user, token):
        user.email_verified=True
        user.save()

        return render(request, 'authentication/activate-success.html', {'user': user})

    return render(request, 'authentication/activate-failed.html', {'user': user})


def order_confirmation_email(user, order, request):
    email_subject = "Order confirmed"
    email_body = render_to_string('confirmation/order_confirm.html', {
        'user': user,
        'order': order
    })

    send_mail_async.delay(email_subject, email_body, settings.EMAIL_FROM_USER, [user.email_login])


class LoginView(APIView):

    # user login
    def post(self, request, *args, **kwargs):
        if {'email_login', 'password'}.issubset(request.data):
            current_customer = Customer.objects.filter(email_login=request.data['email_login']).first()
            if not current_customer:
                return JsonResponse({'Status': False, 'Error': 'Customer with this email does not exist'})
            else:
                if not current_customer.email_verified:
                    if request.data.get('resend_email') == 'True':
                        send_activation_email(current_customer, request)
                        return JsonResponse({'Status': False, 'Error': 'Please confirm your email address'})
                    else:
                        return JsonResponse({'Status': False, 'Error': 'Please request confirmation link again'})
                else:
                    check_pass = check_password(request.data['password'], current_customer.password)
                    if not check_pass:
                        return JsonResponse({'Status': False, 'Error': 'Incorrect password'})
                    if current_customer.is_active:
                        token_ = Token.objects.filter(user=current_customer).first()
                        if token_:
                            token_.delete()
                        token = Token.objects.create(user=current_customer)
                        return JsonResponse({'Status': True, 'Token': token.key, 'Token creation time': token.created})
                    else:
                        return JsonResponse({'Status': False, 'Error': 'Customer is not active'})
        return JsonResponse({'Status': False, 'Error': 'Please provide email and password'})


class ProductViewSet(viewsets.ModelViewSet):

    # get product by slug (stock number), search by name/model, delete product (with auth)
    queryset = Product.objects.all()
    lookup_field = 'slug'
    serializer_class = ProductSerializer
    search_fields = ['name', 'model']

    def get_permissions(self):
        if self.action == "destroy":
            self.permission_classes = [IsLoggedIn]
        return super().get_permissions()


class VendorSupply(APIView):

    permission_classes = [IsLoggedIn,]

    # update vendor's product list
    def post(self, request, *args, **kwargs):
        file = "goods_yaml.yaml"
        import_product_list_async.delay(file, request.data)
        return JsonResponse({'Status': True, 'Message': 'Details will be sent to your email'})


class CustomerSignUp(APIView):

    # user signup
    def post(self, request, *args, **kwargs):
        if {'first_name', 'last_name', 'email_login', 'password', 'user_name', 'phone_number', 'area_code', 'registered_vendor', 'is_active'}.issubset(request.data):
            try:
                validate_password(request.data['password'])
            except forms.ValidationError as password_errors:
                pass_errors = []
                for err in password_errors:
                    pass_errors.append(err)
                return JsonResponse({'Status': False, 'Errors': {'password': pass_errors}})
            request.data._mutable = True
            request.data['password'] = make_password(request.data['password'])
            if request.data['registered_vendor'] == 'True':
                request.data['seller_vendor_id'] = 56120
                # request.data['seller_vendor_id'] = random.randint(200,20000)
            else:
                request.data['seller_vendor_id'] = None
            user_serializer = CustomerSerializer(data=request.data)
            if user_serializer.is_valid():
                current_user = user_serializer.save()
                send_activation_email(current_user, request)
                return Response(user_serializer.data)
            else:
                return JsonResponse({'Status': False, 'Error': user_serializer.errors})
        return JsonResponse({'Status': False, 'Error': 'Please fill all required fields'})


# user view, edit, delete
class CustomerViewSet(viewsets.ModelViewSet):

    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsLoggedIn,]

    def get_object(self):
        return Customer.objects.get(email_login=self.request.data['email_login'])

    # user edit
    def update(self, request, *args, **kwargs):
        request.data._mutable = True
        if request.data.get('password'):
            try:
                validate_password(request.data['password'])
                request.data['password'] = make_password(request.data['password'])
            except forms.ValidationError as password_errors:
                pass_errors = []
                for err in password_errors:
                    pass_errors.append(err)
                return JsonResponse({'Status': False, 'Errors': {'password': pass_errors}})
        current_customer = self.get_object()
        serializer = CustomerSerializer(current_customer, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        else:
            return JsonResponse({'Status': False, 'Error': serializer.errors})


# store view, create, update, delete
class StoreViewSet(viewsets.ModelViewSet):

    queryset = Store.objects.all()
    serializer_class = StoreSerializer
    permission_classes = [IsLoggedIn,]

    def get_object(self):
        current_customer = Customer.objects.filter(email_login=self.request.data['email_login']).first()
        return Store.objects.filter(vendor_id__seller_vendor_id=current_customer.seller_vendor_id).first()

    def get_permissions(self):
        if self.action == "retrieve":
            self.permission_classes = [AllowAny,]
        return super().get_permissions()

    # store delete
    def destroy(self, request, *args, **kwargs):
        current_store = self.get_object()
        if current_store:
            current_store.delete()
            return JsonResponse({'Status': True, 'Message': 'This store has been deleted'})
        return JsonResponse({'Status': False, 'Error': 'Store not found'})

    # store create
    def create(self, request, *args, **kwargs):
        if {'email_login', 'name', 'address', 'url', 'store_cat_id', 'nominal_delivery_price'}.issubset(request.data):
            try:
                current_customer = Customer.objects.filter(email_login=request.data['email_login']).first()
                if not current_customer.registered_vendor:
                    return JsonResponse({'Status': False, 'Error': 'You are not registered as a vendor'})
                else:
                    store_cat = StoreCategory.objects.filter(store_cat_id=request.data['store_cat_id']).first()
                    if not store_cat:
                        return JsonResponse({'Status': False, 'Error': 'Please create a category for this store'})
                    else:
                        request.data._mutable = True
                        request.data['vendor_id'] = current_customer.id
                        request.data['cats'] = store_cat.id
                        current_store = StoreSerializer(data=request.data)
                        if current_store.is_valid():
                            current_store.save()
                            return Response(current_store.data)
                        else:
                            return JsonResponse({'Status': False, 'Error': current_store.errors})
            except ValueError as err:
                return JsonResponse({'Status': False, 'Error': 'Invalid data'})
        return JsonResponse({'Status': False, 'Error': 'Please fill all required fields'})

    # store update
    def update(self, request, *args, **kwargs):
        try:
            if request.data.get('store_cat_id'):
                current_store_cat = StoreCategory.objects.filter(store_cat_id=request.data.get('store_cat_id')).first()
                if not current_store_cat:
                    return JsonResponse({'Status': False, 'Error': 'Store category not found'})
                else:
                    request.data._mutable = True
                    request.data['cats'] = current_store_cat.id
                current_store = self.get_object()
                serializer = StoreSerializer(current_store, data=request.data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    return Response(serializer.data)
                else:
                    return JsonResponse({'Status': False, 'Error': serializer.errors})
        except ValueError as err:
            return JsonResponse({'Status': False, 'Error': 'Invalid data'})


class BasketViewSet(viewsets.ModelViewSet):

    queryset = Basket.objects.all()
    serializer_class = BasketSerializer
    permission_classes = [IsLoggedIn,]

    def get_queryset(self):
        current_customer = Customer.objects.filter(email_login=self.request.data['email_login']).first()
        return Basket.objects.filter(b_customer=current_customer.id).all()

    # basket post
    def post(self, request, *args, **kwargs):
        if {'email_login', 'stock_number', 'amount'}.issubset(request.data):
            current_customer, json_auth_err = custom_authenticate(request.data['email_login'])
            if json_auth_err:
                return json_auth_err
            else:
                try:
                    basket_product = Product.objects.filter(stock_number=request.data['stock_number']).first()
                    basket_vendor = Store.objects.filter(delivery_by_store=basket_product, status=True).first()
                    if basket_product and basket_vendor:
                        new_purchase_item, _ = Basket.objects.update_or_create(b_product=basket_product,
                         b_customer=current_customer,
                         b_vendor=basket_vendor,
                         defaults={'amount': request.data['amount']})
                        basket__ = BasketSerializer(new_purchase_item)
                        return Response(basket__.data)
                    return JsonResponse({'Status': False, 'Errors': 'Product or store not found'})
                except ValueError as err:
                    return JsonResponse({'Status': False, 'Error': 'Invalid data'})
        return JsonResponse({'Status': False, 'Error': 'Please fill all required fields'})

    # basket delete
    def delete(self, request, *args, **kwargs):
        if {'email_login', 'stock_number'}.issubset(request.data):
            current_customer, json_auth_err = custom_authenticate(request.data['email_login'])
            if json_auth_err:
                return json_auth_err
            else:
                try:
                    basket_product = Product.objects.filter(stock_number=request.data['stock_number']).first()
                    basket_item_del = Basket.objects.filter(b_customer=current_customer, b_product=basket_product)
                    if not basket_item_del:
                        return JsonResponse({'Status': False, 'Error': 'Item not found'})
                    else:
                        basket_item_del.delete()
                        return JsonResponse(
                        {'Status': True, 'Message': 'This product has been removed from basket', 'Deleted item': request.data['stock_number']})
                except ValueError:
                    return JsonResponse({'Status': False, 'Error': 'Invalid data'})
        return JsonResponse({'Status': False, 'Error': 'Please fill all required fields'})


class StoreCatView(APIView):

    # store category create/update
    def post(self, request, *args, **kwargs):
        if {'email_login', 'name'}.issubset(request.data):
            current_customer, json_auth_err = custom_authenticate(request.data['email_login'])
            if json_auth_err:
                return json_auth_err
            else:
                try:
                    if request.data.get('store_cat_id'):
                        store_cat_id = request.data.get('store_cat_id')
                    else:
                        store_cat_id = random.randint(100, 2000000)
                    store_cat, _ = StoreCategory.objects.update_or_create(store_cat_id=store_cat_id, defaults={'name': request.data['name']})
                    st_cat__json = StoreCatSerializer(store_cat)
                    return Response(st_cat__json.data)
                except ValueError as err:
                    return JsonResponse({'Status': False, 'Error': 'Invalid data'})
        return JsonResponse({'Status': False, 'Error': 'Please fill all required fields'})

    # store category view
    def get(self, request, *args, **kwargs):
        if {'email_login', 'store_cat_id'}.issubset(request.data):
            current_customer, json_auth_err = custom_authenticate(request.data['email_login'])
            if json_auth_err:
                return json_auth_err
            else:
                try:
                    store_cat = StoreCategory.objects.filter(store_cat_id=request.data['store_cat_id']).first()
                    if store_cat:
                        st_cat__json = StoreCatSerializer(store_cat)
                        return Response(st_cat__json.data)
                    else:
                        return JsonResponse({'Status': False, 'Error': 'Store category not found'})
                except ValueError as err:
                    return JsonResponse({'Status': False, 'Error': 'Invalid data'})
        return JsonResponse({'Status': False, 'Error': 'Please fill all required fields'})

    # store category delete
    def delete(self, request, *args, **kwargs):
        if {'email_login', 'store_cat_id'}.issubset(request.data):
            current_customer, json_auth_err = custom_authenticate(request.data['email_login'])
            if json_auth_err:
                return json_auth_err
            else:
                try:
                    store_cat = StoreCategory.objects.filter(store_cat_id=request.data['store_cat_id']).first()
                    if store_cat:
                        store_check = Store.objects.filter(cats=store_cat).first()
                        if not store_check:
                            store_cat.delete()
                            return JsonResponse({'Status': True, 'Message': 'Store category deleted'})
                        else:
                            return JsonResponse({'Status': False, 'Message': 'Store category not empty'})
                    else:
                        return JsonResponse({'Status': False, 'Error': 'Store category not found'})
                except ValueError as err:
                    return JsonResponse({'Status': False, 'Error': 'Invalid category ID'})
        return JsonResponse({'Status': False, 'Error': 'Please fill all required fields'})


class ProductCatView(APIView):

    # product category view
    def get(self, request, *args, **kwargs):
        if {'email_login', 'prod_cat_id'}.issubset(request.data):
            current_customer, json_auth_err = custom_authenticate(request.data['email_login'])
            if json_auth_err:
                return json_auth_err
            else:
                try:
                    prod_cat__ = ProductCategory.objects.filter(prod_cat_id=request.data['prod_cat_id']).first()
                    if prod_cat__:
                        prod_cat__json = ProdCatSerializer(prod_cat__)
                        return Response(prod_cat__json.data)
                    else:
                        return JsonResponse({'Status': False, 'Error': 'Product category not found'})
                except ValueError as err:
                    return JsonResponse({'Status': False, 'Error': 'Invalid category ID'})
        return JsonResponse({'Status': False, 'Error': 'Please fill all required fields'})

    # product category create/update
    def post(self, request, *args, **kwargs):
        if {'email_login', 'name'}.issubset(request.data):
            current_customer, json_auth_err = custom_authenticate(request.data['email_login'])
            if json_auth_err:
                return json_auth_err
            else:
                try:
                    if request.data.get('prod_cat_id'):
                        prod_cat_id = request.data.get('prod_cat_id')
                    else:
                        prod_cat_id = random.randint(100, 2000000)
                    prod_cat, _ = ProductCategory.objects.update_or_create(prod_cat_id=prod_cat_id, defaults={'name': request.data['name']})
                    prod_cat__json = ProdCatSerializer(prod_cat)
                    return Response(prod_cat__json.data)
                except ValueError as err:
                    return JsonResponse({'Status': False, 'Error': 'Invalid category ID'})
        return JsonResponse({'Status': False, 'Error': 'Please fill all required fields'})

    # product category delete
    def delete(self, request, *args, **kwargs):
        if {'email_login', 'prod_cat_id'}.issubset(request.data):
            current_customer, json_auth_err = custom_authenticate(request.data['email_login'])
            if json_auth_err:
                return json_auth_err
            else:
                try:
                    prod_cat_ = ProductCategory.objects.filter(prod_cat_id=request.data['prod_cat_id']).first()
                    if prod_cat_:
                        products_check = Product.objects.filter(prods=prod_cat_).first()
                        if not products_check:
                            prod_cat_.delete()
                            return JsonResponse({'Status': True, 'Message': 'Product category deleted'})
                        else:
                            return JsonResponse({'Status': False, 'Message': 'Product category not empty'})
                    else:
                        return JsonResponse({'Status': False, 'Error': 'Product category not found'})
                except ValueError as err:
                    return JsonResponse({'Status': False, 'Error': 'Invalid category ID'})
        return JsonResponse({'Status': False, 'Error': 'Please fill all required fields'})


class OrderView(APIView):

    # order create
    def post(self, request, *args, **kwargs):
        if {'email_login', 'express_delivery'}.issubset(request.data):
            current_customer, json_auth_err = custom_authenticate(request.data['email_login'])
            if json_auth_err:
                return json_auth_err
            else:
                basket_ = Basket.objects.filter(b_customer=current_customer)
                if not basket_:
                    return JsonResponse({'Status': False, 'Error': 'Basket empty'})
                else:
                    if not current_customer.address:
                        return JsonResponse({'Status': False, 'Error': 'Please provide customer address'})
                    else:
                        # calculating max nominal delivery price and max weight class for all products in basket; actual delivery price and weight class is equal to the largest figure
                        vendor_nominal_del = []
                        basket_pr_weight = []
                        total_price = 0
                        for basket_item in basket_:
                            vendor_nominal_del.append(basket_item.b_vendor.nominal_delivery_price)
                            basket_pr_weight.append(basket_item.b_product.weight_class)
                        # adding the price of all products in basket
                            total_price += basket_item.b_product.price

                        request.data._mutable = True
                        request.data['order_customer'] = current_customer.id
                        request.data['order_number'] = random.randint(2000,200000000)
                        request.data['status'] = 'new'
                        request.data['area_code'] = current_customer.area_code
                        weight_cl_ = max(basket_pr_weight)
                        del_price = max(vendor_nominal_del)
                        request.data['total_price'] = total_price
                        if request.data['express_delivery'] == "True":
                            express_delivery = 3
                        else:
                            express_delivery = 1
                        request.data['final_delivery_price'] = int(request.data['area_code']) * int(del_price) * int(weight_cl_) * int(express_delivery)

                        order_creation = OrderSerializer(data=request.data, partial=True)
                        if order_creation.is_valid():
                            current_order = order_creation.save()
                        else:
                            return JsonResponse(
                                {'Status': False,
                                 'Error': order_creation.errors})
                        for basket_item in basket_:
                            order_items__ = OrderItemSerializer(data={'number_of_order': current_order.id, 'order_product': basket_item.b_product.id, 'order_prod_vendor': basket_item.b_vendor.id, 'order_prod_amount': basket_item.amount})
                            if order_items__.is_valid():
                                order_items__.save()
                            else:
                                return JsonResponse({'Status': False, 'Error': order_items__.errors})
                        basket_.delete()
                        order_confirmation_email(current_customer, current_order, request)
                        return Response(order_creation.data)
        return JsonResponse({'Status': False, 'Error': 'Please provide express delivery info'})

    # orders view
    def get(self, request, *args, **kwargs):
        if {'email_login'}.issubset(request.data):
            current_customer, json_auth_err = custom_authenticate(request.data['email_login'])
            if json_auth_err:
                return json_auth_err
            else:
                order_set = Order.objects.filter(order_customer=current_customer).all()
                order_set_ser = OrderSerializer(order_set, many=True)
                return Response(order_set_ser.data)
        return JsonResponse({'Status': False, 'Error': 'Please provide email'})

    # order delete
    def delete(self, request, *args, **kwargs):
        if {'email_login', 'order_number'}.issubset(request.data):
            current_customer, json_auth_err = custom_authenticate(request.data['email_login'])
            if json_auth_err:
                return json_auth_err
            else:
                try:
                    order__ = Order.objects.filter(order_number=request.data['order_number'], order_customer=current_customer).first()
                    if order__:
                        if order__.status == 'new' or order__.status == 'confirmed' or order__.status == 'assembled':
                            order__.delete()
                        else:
                            return JsonResponse({'Status': False, 'Error': f'Order {request.data["order_number"]} cannot be deleted as it has already been dispatched. If you dont pick it up, it will be automatically cancelled'})
                        return JsonResponse({'Status': True, 'Message': f'Order {request.data["order_number"]} deleted'})
                    else:
                        return JsonResponse({'Status': False, 'Error': 'Order not found'})
                except ValueError as err:
                    return JsonResponse({'Status': False, 'Error': 'Invalid order number'})
        return JsonResponse({'Status': False, 'Error': 'Please provide order number'})


class OrderDetailView(APIView):

    # view specific order
    def get(self, request, *args, **kwargs):
        if {'email_login', 'order_number'}.issubset(request.data):
            current_customer, json_auth_err = custom_authenticate(request.data['email_login'])
            if json_auth_err:
                return json_auth_err
            else:
                try:
                    order_detail = Order.objects.filter(order_customer=current_customer, order_number=request.data['order_number']).first()
                    if not order_detail:
                        return JsonResponse({'Status': False, 'Error': 'Order not found'})
                    else:
                        order_detail_ser = OrderSerializer(order_detail)
                        return Response(order_detail_ser.data)
                except ValueError as err:
                    return JsonResponse({'Status': False, 'Error': 'Invalid order number'})
        return JsonResponse({'Status': False, 'Error': 'Please fill all required fields'})


class ProductExportView(APIView):

    # export all products by specific vendor
    def get(self, request, *args, **kwargs):
        if {'email_login'}.issubset(request.data):
            current_customer, json_auth_err = custom_authenticate(request.data['email_login'])
            if json_auth_err:
                return json_auth_err
            else:
                file = "export_file.yaml"
                export_product_list_async.delay(file, request.data)
                return JsonResponse({'Status': True, 'Message': 'Details will be sent to your email'})
        return JsonResponse({'Status': False, 'Error': 'Please provide your email address'})
