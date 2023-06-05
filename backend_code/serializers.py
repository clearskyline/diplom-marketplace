from rest_framework import serializers
from backend_code.models import Product, Store, Customer, Basket, StoreCategory, ProductCategory, Order, OrderItems


class CustomerSerializer(serializers.ModelSerializer):

    class Meta:
        model = Customer
        fields = ['id', 'user_name', 'email_login', 'password', 'email_verified', 'first_name', 'last_name', 'phone_number', 'address', 'registered_vendor', 'is_active', 'organization', 'area_code', 'seller_vendor_id']
        read_only_fields = ['id',]
        extra_kwargs = {'password': {'write_only': True, 'min_length': 4}}


class StoreSerializer(serializers.ModelSerializer):
    seller_vendor = serializers.IntegerField(source='vendor_id.seller_vendor_id', read_only=True)

    class Meta:
        model = Store
        fields = ['id', 'vendor_id', 'name', 'address', 'url', 'status', 'seller_vendor', 'cats', 'nominal_delivery_price']


class ProdCatSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProductCategory
        fields = ['id', 'name']


class ProductSerializer(serializers.ModelSerializer):
    delivery_store = serializers.StringRelatedField(source='store.id')
    product_cat = ProdCatSerializer(read_only=True)

    class Meta:
        model = Product
        fields = ['stock_number', 'name', 'model', 'delivery_store', 'amount', 'price', 'recommended_price', 'weight_class', 'product_cat']
        lookup_field = 'slug'
        # extra_kwargs = {'delivery_store': {'read_only': True}}


class BasketSerializer(serializers.ModelSerializer):
    b_customer = serializers.StringRelatedField()
    b_product = serializers.StringRelatedField()
    b_vendor = StoreSerializer(read_only=True)

    class Meta:
        model = Basket
        fields = ['id', 'b_customer', 'b_product', 'b_vendor', 'amount']


class StoreCatSerializer(serializers.ModelSerializer):
    stores = StoreSerializer(read_only=True, many=True)

    class Meta:
        model = StoreCategory
        fields = ['id', 'store_cat_id', 'name', 'stores']


class OrderItemSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrderItems
        fields = ['number_of_order', 'order_product', 'order_prod_vendor', 'order_prod_amount']


class OrderSerializer(serializers.ModelSerializer):
    order_items_number = OrderItemSerializer(read_only=True, many=True)

    class Meta:
        model = Order
        fields = ['order_number', 'order_customer', 'area_code', 'total_price', 'final_delivery_price', 'express_delivery', 'status', 'order_items_number']
