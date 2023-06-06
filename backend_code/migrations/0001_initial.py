# Generated by Django 2.2.16 on 2023-06-06 07:27

from django.conf import settings
import django.contrib.auth.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Customer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('email_login', models.EmailField(max_length=254, unique=True)),
                ('email_verified', models.BooleanField(default=False)),
                ('password', models.CharField(max_length=100)),
                ('user_name', models.CharField(error_messages={'unique': 'Customer with this email already exists.'}, max_length=150, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()])),
                ('first_name', models.CharField(max_length=150)),
                ('last_name', models.CharField(max_length=150)),
                ('phone_number', models.CharField(max_length=150)),
                ('address', models.CharField(blank=True, max_length=500, null=True)),
                ('registered_vendor', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('organization', models.CharField(blank=True, max_length=150)),
                ('area_code', models.PositiveIntegerField()),
                ('seller_vendor_id', models.PositiveIntegerField(blank=True, null=True, unique=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Basket',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.PositiveIntegerField()),
                ('b_customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='b_cust', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order_number', models.PositiveIntegerField(unique=True)),
                ('area_code', models.PositiveIntegerField()),
                ('final_delivery_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('express_delivery', models.BooleanField(default=False)),
                ('total_price', models.PositiveIntegerField()),
                ('status', models.CharField(choices=[('new', 'NEW'), ('confirmed', 'CONFIRMED'), ('assembled', 'ASSEMBLED'), ('dispatched', 'DISPATCHED'), ('delivered', 'DELIVERED'), ('canceled', 'CANCELED')], max_length=30)),
                ('order_customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='order_by_customer', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stock_number', models.PositiveIntegerField(unique=True)),
                ('slug', models.SlugField(max_length=100, unique=True, verbose_name='product_URL')),
                ('name', models.CharField(max_length=250)),
                ('model', models.CharField(blank=True, max_length=250, null=True)),
                ('amount', models.PositiveIntegerField()),
                ('price', models.PositiveIntegerField()),
                ('weight_class', models.PositiveIntegerField()),
                ('recommended_price', models.PositiveIntegerField()),
                ('custom_description', models.TextField(blank=True, null=True)),
                ('basket_product_item', models.ManyToManyField(related_name='product_basket', through='backend_code.Basket', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Product',
                'verbose_name_plural': 'Products',
                'ordering': ('-name',),
            },
        ),
        migrations.CreateModel(
            name='ProductCategory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('prod_cat_id', models.PositiveIntegerField(unique=True)),
                ('name', models.CharField(max_length=50)),
            ],
            options={
                'verbose_name': 'Product category',
                'verbose_name_plural': 'Product categories',
                'ordering': ('-name',),
            },
        ),
        migrations.CreateModel(
            name='Store',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('address', models.CharField(max_length=250)),
                ('url', models.URLField(blank=True, null=True)),
                ('nominal_delivery_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('status', models.BooleanField(default=True)),
                ('vendor_id', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='unique_vendor_id', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Store',
                'verbose_name_plural': 'Stores',
                'ordering': ('-name',),
            },
        ),
        migrations.CreateModel(
            name='StoreCategory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('store_cat_id', models.PositiveIntegerField(unique=True)),
                ('name', models.CharField(max_length=50)),
                ('store_cat_creator', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='st_c_creator', to=settings.AUTH_USER_MODEL)),
                ('stores', models.ManyToManyField(blank=True, related_name='cats', to='backend_code.Store')),
            ],
            options={
                'verbose_name': 'Store category',
                'verbose_name_plural': 'Store categories',
                'ordering': ('-name',),
            },
        ),
        migrations.CreateModel(
            name='ProductParameters',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('screen_size', models.DecimalField(decimal_places=2, max_digits=4)),
                ('dimension', models.CharField(max_length=30)),
                ('RAM', models.PositiveIntegerField()),
                ('color', models.CharField(max_length=50)),
                ('pr_id', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='prod_pars', to='backend_code.Product')),
            ],
        ),
        migrations.AddField(
            model_name='product',
            name='custom_parameters',
            field=models.ManyToManyField(related_name='parameters_by_product', to='backend_code.ProductParameters'),
        ),
        migrations.AddField(
            model_name='product',
            name='delivery_store',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='delivery_by_store', to='backend_code.Store'),
        ),
        migrations.AddField(
            model_name='product',
            name='product_cat',
            field=models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, related_name='pr_category', to='backend_code.ProductCategory'),
        ),
        migrations.CreateModel(
            name='OrderItems',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order_slug', models.SlugField(max_length=100, verbose_name='order_URL')),
                ('order_prod_vendor', models.CharField(max_length=100)),
                ('order_prod_amount', models.PositiveIntegerField()),
                ('number_of_order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='order_items_number', to='backend_code.Order')),
                ('order_product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='product_by_order', to='backend_code.Product')),
            ],
            options={
                'verbose_name': 'Order items',
                'verbose_name_plural': 'Orders items',
                'ordering': ('-number_of_order',),
            },
        ),
        migrations.AddField(
            model_name='basket',
            name='b_product',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='b_pr', to='backend_code.Product'),
        ),
        migrations.AddField(
            model_name='basket',
            name='b_vendor',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='b_vend', to='backend_code.Store'),
        ),
        migrations.AddField(
            model_name='customer',
            name='basket_customer_item',
            field=models.ManyToManyField(related_name='customer_basket', through='backend_code.Basket', to='backend_code.Product'),
        ),
    ]
