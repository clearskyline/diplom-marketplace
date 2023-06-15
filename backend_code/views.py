import json
import random
import threading

import requests.utils
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.password_validation import validate_password
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.core.serializers import get_serializer
from django.core.serializers.json import DjangoJSONEncoder
from django.db import IntegrityError
from django.db.models import Q
from django.forms import forms
from django.template.loader import render_to_string
from django.utils.datastructures import MultiValueDictKeyError
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets, status
from rest_framework.authtoken.models import Token
from django.http import JsonResponse
from django.shortcuts import render, redirect
from rest_framework.decorators import action, permission_classes, api_view
from rest_framework.generics import RetrieveDestroyAPIView, get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from datetime import datetime, timedelta
import yaml
from rest_framework.viewsets import ViewSet

from backend_code.models import Product, ProductCategory, Store, Customer, Basket, ProductParameters, StoreCategory, \
    Order, OrderItems
from backend_code.permissions import IsLoggedIn, IsProductOwner, IsStoreCatOwner, IsOrderOwner
from backend_code.serializers import ProductSerializer, CustomerSerializer, StoreSerializer, BasketSerializer, \
    StoreCatSerializer, ProdCatSerializer, OrderSerializer, OrderDetailSerializer
from backend_code.token_gen import generate_token

from backend_code.tasks import send_mail_async, import_product_list_async, export_product_list_async


def send_activation_email(user, request):
    '''
    Отправка имейла после регистрации пользователя. Сообщение содержит ссылку для подтверждения адреса пользователя (необходимо для авторизации и дальнейшей работы).
    '''
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
    '''
    Отправка имейла для подтверждения заказа. Сообщение носит информативный характер, содержит сведения о пользователе и заказе.
    '''
    email_subject = "Order confirmed"
    email_body = render_to_string('confirmation/order_confirm.html', {
        'user': user,
        'order': order
    })

    send_mail_async.delay(email_subject, email_body, settings.EMAIL_FROM_USER, [user.email_login])


@extend_schema(tags=["Пользователь"], summary="Аутентификация пользователя")
class LoginView(APIView):
    '''
    Аутентификация пользователя. Требуется ввести имейл и пароль. Для успешной аутентификации необходимо сначала зарегистрироваться (class CustomerSignUp, path('user-signup/')) и подтвердить имейл по ссылке, которая приходит на указанный адрес.
    '''
    def post(self, request, *args, **kwargs):
        if {'email_login', 'password'}.issubset(request.data):
            current_customer = Customer.objects.filter(email_login=request.data['email_login']).first()
            if not current_customer:
                return JsonResponse({'Status': False, 'Error': 'Customer with this email does not exist'}, status=401)
            else:
                if not current_customer.email_verified:
                    if request.data.get('resend_email') == 'True':
                        send_activation_email(current_customer, request)
                        return JsonResponse({'Status': False, 'Error': 'Please confirm your email address'}, status=401)
                    else:
                        return JsonResponse({'Status': False, 'Error': 'Please request confirmation link again'}, status=401)
                else:
                    check_pass = check_password(request.data['password'], current_customer.password)
                    if not check_pass:
                        return JsonResponse({'Status': False, 'Error': 'Incorrect password'}, status=401)
                    if current_customer.is_active:
                        token_ = Token.objects.filter(user=current_customer).first()
                        if token_:
                            token_.delete()
                        token = Token.objects.create(user=current_customer)
                        return JsonResponse({'Status': True, 'Token': token.key, 'Token creation time': token.created}, status=200)
                    else:
                        return JsonResponse({'Status': False, 'Error': 'Customer is not active'}, status=401)
        return JsonResponse({'Status': False, 'Error': 'Please provide email and password'}, status=401)


@extend_schema(tags=['Товар'])
@extend_schema_view(
    retrieve=extend_schema(
        summary='Поиск товара по "слагу" (артикулу - stock number), названию или модели'),
    destroy=extend_schema(
        summary='Удаление товара (требуется аутентификация)'))
class ProductViewSet(viewsets.ModelViewSet):
    '''
    С помощью данного url пользователь может найти товар по "слагу" (артикулу - stock number), а также найти товар по названию или модели (например, goods/?s=iphone). Для этих действий аутентифиация не требуется. Для удаления товара требуется аутентификация пользователя в системе, кроме того, пользователь должен быть владельцем этого товара (IsProductOwner).
    '''
    queryset = Product.objects.all()
    lookup_field = 'slug'
    serializer_class = ProductSerializer
    search_fields = ['name', 'model']

    def get_permissions(self):
        if self.action == "destroy":
            self.permission_classes = [IsLoggedIn, IsProductOwner,]
        return super().get_permissions()


@extend_schema(tags=["Импорт товаров"], summary="Импорт списка товаров поставщика")
class VendorSupply(APIView):
    '''
    Импорт списка товаров поставщика из файла yaml. Для успешного импорта идентификатор текущего пользователя (vendor_id) должен соответствовать идентификатору (vendor_id) в файле yaml. Функция выполняется асинхронно с помощью celery. Пользователь получает имейл с информацией об успешном или неуспешном завершении операции. При этом работа программы не останавливается.
    '''
    permission_classes = [IsLoggedIn,]

    # update vendor's product list
    def post(self, request, *args, **kwargs):
        file = "goods_yaml.yaml"
        import_product_list_async.delay(file, request.data)
        return JsonResponse({'Status': True, 'Message': 'Details will be sent to your email'})


@extend_schema(tags=["Пользователь"], summary="Регистрация нового пользователя")
class CustomerSignUp(APIView):
    '''
    Регистрация нового пользователя. Необходимо указать все обязательные данные. В качестве логина для авторизации и идентификатора пользователя в системе используется адрес эл. почты.
    '''
    def post(self, request, *args, **kwargs):
        if {'first_name', 'last_name', 'email_login', 'password', 'user_name', 'phone_number', 'area_code', 'registered_vendor', 'is_active'}.issubset(request.data):
            try:
                validate_password(request.data['password'])
            except forms.ValidationError as password_errors:
                pass_errors = []
                for err in password_errors:
                    pass_errors.append(err)
                return JsonResponse({'Status': False, 'Errors': {'password': pass_errors}}, status=401)
            request.data._mutable = True
            request.data['password'] = make_password(request.data['password'])
            if request.data['registered_vendor'] == 'True':
                # request.data['seller_vendor_id'] = 56120
                request.data['seller_vendor_id'] = random.randint(200,20000)
            else:
                request.data['seller_vendor_id'] = None
            user_serializer = CustomerSerializer(data=request.data)
            if user_serializer.is_valid():
                current_user = user_serializer.save()
                send_activation_email(current_user, request)
                return Response(user_serializer.data, status=201)
            else:
                return JsonResponse({'Status': False, 'Error': user_serializer.errors}, status=401)
        return JsonResponse({'Status': False, 'Error': 'Please fill all required fields'}, status=401)


@extend_schema(tags=['Пользователь'])
@extend_schema_view(
    retrieve=extend_schema(
        summary='Получение информации о пользователе'),
    destroy=extend_schema(
        summary='Удаление пользователя'),
    update=extend_schema(
        summary='Обновление информации о пользователе'))
class CustomerViewSet(viewsets.ModelViewSet):
    '''
    По этому url можно получить информацию о пользователе, обновить информацию о пользователе и удалить пользователя. Для всех действий требуется аутентификация. Действия доступны только для текущего пользователя (для других пользователей выполнить эти действия невозможно).
    '''
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsLoggedIn,]

    def get_object(self):
        print(self.request.data)
        return Customer.objects.get(email_login=self.request.data.get('email_login'))

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
                return JsonResponse({'Status': False, 'Errors': {'password': pass_errors}}, status=401)
        current_customer = self.get_object()
        if request.data.get('registered_vendor') == 'True' and not current_customer.seller_vendor_id:
            # request.data['seller_vendor_id'] = 56120
            request.data['seller_vendor_id'] = random.randint(200,20000)
        serializer = CustomerSerializer(current_customer, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        else:
            return JsonResponse({'Status': False, 'Error': serializer.errors}, status=401)


@extend_schema(tags=['Магазин'])
@extend_schema_view(
    retrieve=extend_schema(
        summary='Получение информации о магазине'),
    destroy=extend_schema(
        summary='Удаление магазина'),
    update=extend_schema(
        summary='Обновление информации о магазине'),
    create=extend_schema(
        summary='Создание магазина'))
class StoreViewSet(viewsets.ModelViewSet):
    '''
    По этому url можно создать магазин, получить информацию о магазине, обновить информацию о магазине, удалить магазин. Для создания магазина пользователь должен быть зарегистрирован как продавец (current_customer.registered_vendor = True) Для просмотра магазина аутентификация не нужна. Изменить и удалить магазин может только его владелец. Чтобы создать и обновить магазин, соответствующая категория магазина должна быть создана.
    '''
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
            return JsonResponse({'Status': True, 'Message': 'This store has been deleted'}, status=200)
        return JsonResponse({'Status': False, 'Error': 'Store not found'}, status=404)

    # store create
    def create(self, request, *args, **kwargs):
        if {'email_login', 'name', 'address', 'store_cat_id', 'nominal_delivery_price'}.issubset(request.data):
            try:
                current_customer = Customer.objects.filter(email_login=request.data['email_login']).first()
                if not current_customer.registered_vendor:
                    return JsonResponse({'Status': False, 'Error': 'You are not registered as a vendor'}, status=401)
                else:
                    store_cat = StoreCategory.objects.filter(store_cat_id=request.data['store_cat_id']).first()
                    if not store_cat:
                        return JsonResponse({'Status': False, 'Error': 'Please create a category for this store'}, status=401)
                    else:
                        request.data._mutable = True
                        request.data['vendor_id'] = current_customer.id
                        request.data['cats'] = store_cat.id
                        current_store = StoreSerializer(data=request.data)
                        if current_store.is_valid():
                            current_store.save()
                            return Response(current_store.data, status=200)
                        else:
                            return JsonResponse({'Status': False, 'Error': current_store.errors}, status=401)
            except ValueError as err:
                return JsonResponse({'Status': False, 'Error': 'Invalid data'}, status=401)
        return JsonResponse({'Status': False, 'Error': 'Please fill all required fields'}, status=401)

    # store update
    def update(self, request, *args, **kwargs):
        current_store = self.get_object()
        if current_store:
            try:
                if request.data.get('store_cat_id'):
                    current_store_cat = StoreCategory.objects.filter(store_cat_id=request.data.get('store_cat_id')).first()
                    if not current_store_cat:
                        return JsonResponse({'Status': False, 'Error': 'Store category not found'}, status=404)
                    else:
                        request.data._mutable = True
                        request.data['cats'] = current_store_cat.id
                serializer = StoreSerializer(current_store, data=request.data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    return Response(serializer.data, status=200)
                else:
                    return JsonResponse({'Status': False, 'Error': serializer.errors}, status=401)
            except ValueError as err:
                return JsonResponse({'Status': False, 'Error': 'Invalid data'}, status=401)
        else:
            return JsonResponse({'Status': False, 'Error': 'Store not found'}, status=404)


@extend_schema(tags=['Корзина'])
@extend_schema_view(
    list=extend_schema(
        summary='Список товаров в корзине'),
    destroy=extend_schema(
        summary='Удаление одного товара из корзины'),
    create=extend_schema(
        summary='Добавление товара в корзину, обновление товара в корзине'))
class BasketViewSet(viewsets.ModelViewSet):
    '''
    По этому url можно получить список товаров в корзине для текущего пользователя, добавить товар в корзину (обновить товар в корзине) и удалить товар из корзины. Для всех действий требуется аутентификация. Для обработки запроса list надо указать имейл пользователя, для destroy - имейл и актикул товара (stock_number), для create - имейл, артикул и количество товара. Метод POST (create) обрабатывает запросы на добавление и обновление товара в корзине. Артикул товара передается не через "слаг", а через тело запроса.
    '''
    queryset = Basket.objects.all()
    serializer_class = BasketSerializer
    permission_classes = [IsLoggedIn,]

    def get_queryset(self):
        current_customer = Customer.objects.filter(email_login=self.request.data['email_login']).first()
        return Basket.objects.filter(b_customer=current_customer.id).all()

    # basket create and update
    def create(self, request, *args, **kwargs):
        if {'stock_number', 'amount'}.issubset(request.data):
            try:
                current_customer = Customer.objects.filter(email_login=self.request.data['email_login']).first()
                basket_product = Product.objects.filter(stock_number=request.data['stock_number']).first()
                basket_vendor = Store.objects.filter(delivery_by_store=basket_product, status=True).first()
                if basket_product and basket_vendor:
                    new_purchase_item, _ = Basket.objects.update_or_create(b_product=basket_product,
                     b_customer=current_customer,
                     b_vendor=basket_vendor,
                     defaults={'amount': request.data['amount']})
                    basket_serializer = BasketSerializer(new_purchase_item)
                    return Response(basket_serializer.data, status=200)
                return JsonResponse({'Status': False, 'Errors': 'Product or store not found'}, status=404)
            except ValueError as err:
                return JsonResponse({'Status': False, 'Error': 'Invalid data'}, status=401)
        return JsonResponse({'Status': False, 'Error': 'Please fill all required fields'}, status=401)

    # basket delete
    def destroy(self, request, *args, **kwargs):
        if {'stock_number'}.issubset(request.data):
            try:
                current_item = self.get_queryset().filter(b_product__stock_number=request.data['stock_number']).first()
                if current_item:
                    current_item.delete()
                    return JsonResponse({'Status': True, 'Message': 'Item removed from basket'}, status=200)
                else:
                    return JsonResponse({'Status': False, 'Error': 'Item not found'}, status=404)
            except ValueError as err:
                return JsonResponse({'Status': False, 'Error': 'Invalid data'}, status=401)
        return JsonResponse({'Status': False, 'Error': 'Please fill all required fields'}, status=401)


@extend_schema(tags=['Категория магазина'])
@extend_schema_view(
    retrieve=extend_schema(
        summary='Подробная информация о категории магазина'),
    destroy=extend_schema(
        summary='Удаление категории магазина'),
    create=extend_schema(
        summary='Создание или обновление категории магазина'))
class StoreCatViewSet(viewsets.ModelViewSet):
    '''
    По этому url можно посмотреть сведения о категории магазина (включая все соответствующие магазины), создать (обновить) категорию магазина и удалить категорию магазина. У каждой категории магазина есть владелец (пользователь, создавший категорию - IsStoreCatOwner). Только он может выполнять действия с соответствующей категорией магазина.
    '''
    queryset = StoreCategory.objects.all()
    serializer_class = StoreCatSerializer
    permission_classes = [IsLoggedIn, IsStoreCatOwner,]

    def get_object(self):
        obj = get_object_or_404(StoreCategory, store_cat_id=self.request.data['store_cat_id'])
        self.check_object_permissions(self.request, obj)
        return obj

    # store category create/update
    def create(self, request, *args, **kwargs):
        if {'name'}.issubset(request.data):
            try:
                if request.data.get('store_cat_id'):
                    try:
                        store_cat_id = int(request.data.get('store_cat_id'))
                    except ValueError as err:
                        store_cat_id = random.randint(100, 2000000)
                else:
                    store_cat_id = random.randint(100, 2000000)
                current_customer = Customer.objects.filter(email_login=request.data['email_login']).first()
                store_cat, _ = StoreCategory.objects.update_or_create(store_cat_id=store_cat_id, store_cat_creator=current_customer, defaults={'name': request.data['name']})
                store_cat__ser = StoreCatSerializer(store_cat)
                return Response(store_cat__ser.data, status=200)
            except IntegrityError as err:
                return JsonResponse({'Status': False, 'Error': 'Category cannot be updated.'}, status=406)
        return JsonResponse({'Status': False, 'Error': 'Please fill all required fields'}, status=401)

    # store category delete
    def destroy(self, request, *args, **kwargs):
        if {'store_cat_id'}.issubset(request.data):
            try:
                store_cat = self.get_object()
                if store_cat:
                    store_check = Store.objects.filter(cats=store_cat).first()
                    if not store_check:
                        store_cat.delete()
                        return JsonResponse({'Status': True, 'Message': 'Store category deleted'}, status=200)
                    else:
                        return JsonResponse({'Status': False, 'Message': 'Store category not empty'}, status=406)
                else:
                    return JsonResponse({'Status': False, 'Error': 'Store category not found'}, status=404)
            except KeyError as err:
                return JsonResponse({'Status': False, 'Error': 'Invalid data'}, status=401)
        return JsonResponse({'Status': False, 'Error': 'Please fill all required fields'}, status=401)


@extend_schema(tags=['Категория товара'])
@extend_schema_view(
    retrieve=extend_schema(
        summary='Информация о категории товара'),
    destroy=extend_schema(
        summary='Удаление категории товара'),
    create=extend_schema(
        summary='Создание или обновление категории товара'))
# product category view, create/update, delete
class ProductCatViewSet(viewsets.ModelViewSet):
    '''
    По данному url можно просмотреть сведения о категории товара (ИД и название), удалить категорию товара, создать или обновить категорию товара. Для просмотра категории аутентификация не требуется (AllowAny). Для остальных действий необходима аутентификация. Создание и обновление выполняется с помощью одного метода POST (create). Если при создании номер категории не указан, он будет сгенерирован автоматически.
    '''
    queryset = ProductCategory.objects.all()
    serializer_class = ProdCatSerializer
    permission_classes = [IsLoggedIn,]

    def get_object(self):
        try:
            obj = get_object_or_404(ProductCategory, prod_cat_id=self.request.data['prod_cat_id'])
            return obj
        except ValueError as err:
            return None

    def get_permissions(self):
        if self.action == "retrieve":
            self.permission_classes = [AllowAny,]
        return super().get_permissions()

    # product category create/update
    def create(self, request, *args, **kwargs):
        if {'name'}.issubset(request.data):
            if request.data.get('prod_cat_id'):
                prod_cat_id = request.data.get('prod_cat_id')
            else:
                prod_cat_id = random.randint(100, 2000000)
            try:
                prod_cat, _ = ProductCategory.objects.update_or_create(prod_cat_id=prod_cat_id, defaults={'name': request.data['name']},)
                return Response(ProdCatSerializer(prod_cat).data, status=200)
            except ValueError as err:
                return JsonResponse({'Status': False, 'Error': 'Invalid data'}, status=401)
        return JsonResponse({'Status': False, 'Error': 'Please fill all required fields'}, status=401)

    # product category delete
    def destroy(self, request, *args, **kwargs):
        if {'prod_cat_id'}.issubset(request.data):
            try:
                current_pr_cat = self.get_object()
                if current_pr_cat:
                    current_pr_cat.delete()
                    return JsonResponse({'Status': True, 'Message': 'Product category deleted'}, status=200)
                else:
                    return JsonResponse({'Status': False, 'Error': 'Product category not found'}, status=404)
            except ValueError as err:
                    return JsonResponse({'Status': False, 'Error': 'Invalid data'}, status=401)
        return JsonResponse({'Status': False, 'Error': 'Please fill all required fields'}, status=401)


@extend_schema(tags=['Заказ'])
@extend_schema_view(
    destroy=extend_schema(
        summary='Удаление заказа пользователя'),
    create=extend_schema(
        summary='Создание заказа пользователя'))
class OrderViewSet(viewsets.ModelViewSet):
    '''
    По данному url можно просмотреть список заказов пользователя, удалить заказ и создать заказ. Изменение созданного заказа в программе не предусмотрено. Пользователь может удалить свой заказ, только если он еще не был отгружен (dispatched). При создании заказа надо указать параметр "экспресс-доставки" (True/False). При создании заказа стоимость доставки рассчитывается в зависимости от поставщика, габаритов (weight_class), региона (area_code) и экспресс-доставки. После создания заказа корзина автоматически очищается. Если корзина пуста или пользователь не указал при регистрации свой адрес, заказ не оформляется. Метод GET (order_list) выдает сведения обо всех заказах пользователя (без деталей). Для выполнения всех действий требуется аутентификация. Для просмотра заказов и удаления заказа пользователь должен быть владельцем заказа (IsOrderOwner).
    '''
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsLoggedIn, IsOrderOwner]

    def get_queryset(self):
        return Order.objects.filter(order_customer__email_login=self.request.data['email_login']).all()

    # order create
    def create(self, request, *args, **kwargs):
        if {'express_delivery'}.issubset(request.data):
            current_customer = Customer.objects.filter(email_login=request.data['email_login']).first()
            basket_ = Basket.objects.filter(b_customer=current_customer)
            if not basket_:
                return JsonResponse({'Status': False, 'Error': 'Basket empty'}, status=404)
            else:
                if not current_customer.address:
                    return JsonResponse({'Status': False, 'Error': 'Please provide customer address'}, status=401)
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
                                 'Error': order_creation.errors}, status=401)
                    for basket_item in basket_:
                        current_product = Product.objects.filter(id=basket_item.b_product.id).first()
                        order_item = OrderItems.objects.create(number_of_order=current_order, order_product=current_product, order_prod_vendor=basket_item.b_vendor, order_prod_amount=basket_item.amount)
                    basket_.delete()
                    order_confirmation_email(current_customer, current_order, request)
                    return Response(order_creation.data, status=201)
        return JsonResponse({'Status': False, 'Error': 'Please provide express delivery info'}, status=401)

    # orders view
    @extend_schema(summary="Список заказов пользователя")
    def order_list(self, request, *args, **kwargs):
        order_set = self.get_queryset()
        if order_set:
            order_set_ser = OrderSerializer(order_set, many=True)
            return Response(order_set_ser.data, status=200)
        else:
            return JsonResponse({'Status': False, 'Error': 'You have no orders'}, status=404)

    # order delete
    def destroy(self, request, *args, **kwargs):
        if {'order_number'}.issubset(request.data):
            try:
                current_order = self.get_queryset().filter(order_number=request.data['order_number']).first()
                if not current_order:
                    return JsonResponse({'Status': False, 'Error': 'Order not found'}, status=404)
                else:
                    if current_order.status == 'new' or current_order.status == 'confirmed' or current_order.status == 'assembled':
                        current_order.delete()
                        return JsonResponse({'Status': True, 'Message': 'Order deleted'}, status=200)
                    else:
                        return JsonResponse({'Status': False, 'Error': f'Order {request.data["order_number"]} cannot be deleted as it has already been dispatched. If you dont pick it up, it will be automatically cancelled'}, status=406)
            except ValueError as err:
                return JsonResponse({'Status': False, 'Error': 'Invalid data'}, status=401)
        return JsonResponse({'Status': False, 'Error': 'Please provide order number'}, status=401)


@extend_schema(tags=['Подробности заказа'])
@extend_schema_view(
    retrieve=extend_schema(
        summary='Детали одного заказа пользователя'))
class OrderDetailViewSet(viewsets.ModelViewSet):
    '''
    По этому url можно просмотреть полные сведения об определенном заказе пользователя. Номер заказа передается через slug. Для просмотра требуется аутентификация, кроме того, пользователь должен быть владельцем заказа (IsOrderOwner). Информация о товарах в заказе выводится с помощью сериализаторов OrderItemSerializer, ProductSerializer.
    '''
    queryset = Order.objects.all()
    serializer_class = OrderDetailSerializer
    lookup_field = 'order_slug'
    permission_classes = [IsLoggedIn, IsOrderOwner]


@extend_schema(tags=["Экспорт товаров"], summary="Экспорт списка товаров поставщика и отправка на имейл")
class ProductExportViewSet(viewsets.ModelViewSet):
    '''
    Экспорт списка товаров поставщика в файл yaml и отправка в виде вложения на его адрес эл. почты. Функция выполняется асинхронно с помощью celery. При этом работа программы не останавливается.
    '''
    permission_classes = [IsLoggedIn,]

    # export all products by specific vendor
    def export_product_list(self, request, *args, **kwargs):
        file = "export_file.yaml"
        export_product_list_async.delay(file, request.data)
        return JsonResponse({'Status': True, 'Message': 'Details will be sent to your email'})
