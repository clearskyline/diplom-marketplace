from django.contrib.auth.models import AbstractBaseUser, AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.template.defaultfilters import slugify

STATUS_CHOICES = (
    ('new', 'NEW'),
    ('confirmed', 'CONFIRMED'),
    ('assembled', 'ASSEMBLED'),
    ('dispatched', 'DISPATCHED'),
    ('delivered', 'DELIVERED'),
    ('canceled', 'CANCELED'),
)


class Store(models.Model):
    vendor_id = models.OneToOneField('Customer', related_name='unique_vendor_id', on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    address = models.CharField(max_length=250)
    url = models.URLField(null=True, blank=True)
    nominal_delivery_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Store'
        verbose_name_plural = 'Stores'
        ordering = ('-name',)

    def __str__(self):
        return self.name


class StoreCategory(models.Model):
    store_cat_id = models.PositiveIntegerField()
    name = models.CharField(max_length=50)
    stores = models.ManyToManyField(Store, related_name='cats', blank=True)

    class Meta:
        verbose_name = 'Store category'
        verbose_name_plural = 'Store categories'
        ordering = ('-name',)

    def __str__(self):
        return self.name


class ProductParameters(models.Model):
    pr_id = models.OneToOneField('Product', related_name='prod_pars', on_delete=models.CASCADE)
    screen_size = models.DecimalField(max_digits=4, decimal_places=2)
    dimension = models.CharField(max_length=30)
    RAM = models.PositiveIntegerField()
    color = models.CharField(max_length=50)


class Product(models.Model):
    stock_number = models.PositiveIntegerField(unique=True)
    slug = models.SlugField(unique=True, max_length=100, db_index=True, verbose_name='product_URL')
    name = models.CharField(max_length=250)
    model = models.CharField(max_length=250, null=True, blank=True)
    delivery_store = models.ManyToManyField(Store, related_name='delivery_by_store')
    amount = models.PositiveIntegerField()
    price = models.PositiveIntegerField()
    weight_class = models.PositiveIntegerField()
    recommended_price = models.PositiveIntegerField()
    custom_parameters = models.ManyToManyField(ProductParameters, related_name='parameters_by_product')
    custom_description = models.TextField(null=True, blank=True)
    basket_product_item = models.ManyToManyField('Customer', related_name='product_basket', through='Basket')

    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ('-name',)

    def save(self, *args, **kwargs):
        self.slug = slugify(self.stock_number)
        super(Product, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.stock_number} ({self.name} - {self.price} руб.)'


class ProductCategory(models.Model):
    prod_cat_id = models.PositiveIntegerField()
    name = models.CharField(max_length=50)
    products_by_cat = models.ManyToManyField(Product, related_name='prods', blank=True)

    class Meta:
        verbose_name = 'Product category'
        verbose_name_plural = 'Product categories'
        ordering = ('-name',)

    def __str__(self):
        return self.name


class Customer(AbstractBaseUser):
    REQUIRED_FIELDS = []
    username = None
    email_login = models.EmailField(unique=True)
    USERNAME_FIELD = 'email_login'
    email_verified = models.BooleanField(default=False)
    password = models.CharField(max_length=100, null=False)
    user_name_validation = UnicodeUsernameValidator()
    user_name = models.CharField(max_length=150, validators=[user_name_validation], error_messages={'unique': ("Customer with this email already exists.")})
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=150)
    address = models.CharField(max_length=500, null=True, blank=True)
    registered_vendor = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    organization = models.CharField(max_length=150, blank=True)
    area_code = models.PositiveIntegerField()
    seller_vendor_id = models.PositiveIntegerField(unique=True, null=True, blank=True)
    basket_customer_item = models.ManyToManyField(Product, related_name='customer_basket', through='Basket')

    def __str__(self):
        return self.user_name


class Basket(models.Model):
    b_customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='b_cust')
    b_product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='b_pr')
    b_vendor = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='b_vend')
    amount = models.PositiveIntegerField()

    def __str__(self):
        return f'{self.b_customer}, {self.b_product}, {self.b_vendor}, {self.amount}'


class Order(models.Model):
    order_number = models.PositiveIntegerField(unique=True)
    order_customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='order_by_customer')
    area_code = models.PositiveIntegerField()
    final_delivery_price = models.DecimalField(max_digits=10, decimal_places=2)
    express_delivery = models.BooleanField(default=False)
    total_price = models.PositiveIntegerField()
    status = models.CharField(choices=STATUS_CHOICES, max_length=30)

    def __str__(self):
        return self.order_number


class OrderItems(models.Model):
    number_of_order = models.ForeignKey(Order, related_name='order_items_number', on_delete=models.CASCADE)
    order_product = models.CharField(max_length=100)
    order_prod_vendor = models.CharField(max_length=100)
    order_prod_amount = models.PositiveIntegerField()
