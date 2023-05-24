import yaml
from celery import shared_task
from django.core.mail import send_mail
import time

from django.http import JsonResponse
from django.template.loader import render_to_string

from backend_code.models import ProductCategory, Product, ProductParameters, Store, Customer
from marketplace import settings


@shared_task()
def send_mail_async(subject, body, from_email, to):
    time.sleep(2)
    send_mail(subject, body, from_email, to)


@shared_task()
def import_product_list_async(file, data):
    current_customer = Customer.objects.filter(email_login=data['email_login']).first()
    from_email = settings.EMAIL_FROM_USER
    to = [current_customer.email_login]
    try:
        store_check = Store.objects.filter(vendor_id=current_customer).first()
        if not current_customer.is_active or not store_check:
            subject = 'Product list import failed'
            body = render_to_string('import_export/import.html', {
                'user': current_customer,
                'message_body': 'Vendor or store is not active'})
            send_mail_async(subject, body, from_email, to)
            return 'Vendor or store is not active'
        else:
            with open(file, "r") as stream:
                try:
                    data_loaded = yaml.safe_load(stream)
                except yaml.YAMLError as exc:
                    subject = 'Product list import failed'
                    body = render_to_string('import_export/import.html', {
                        'user': current_customer,
                        'message_body': f'Data error - {exc}.'})
                    send_mail_async(subject, body, from_email, to)
                    return 'Data error'
            if current_customer.seller_vendor_id != data_loaded['vendor_id']:
                subject = 'Product list import failed'
                body = render_to_string('import_export/import.html', {
                    'user': current_customer,
                    'message_body': 'You cannot import product list for this vendor.'})
                send_mail_async(subject, body, from_email, to)
                return 'This customer cannot import products for this vendor'
            else:
                skipped = 0
                for cat in data_loaded['categories']:
                    prod_cat, _ = ProductCategory.objects.update_or_create(prod_cat_id=cat['prod_cat_id'], defaults={'name': cat['name']})
                    prod_cat.save()
                for item in data_loaded['goods']:
                    check_article_not_unique = Product.objects.filter(stock_number=item['stock_number']).exclude(
                        delivery_store=current_customer.unique_vendor_id)
                    if check_article_not_unique:
                        skipped += 1
                    else:
                        current_pr_cat = ProductCategory.objects.filter(prod_cat_id=item['category']).first()
                        current_item, _ = Product.objects.update_or_create(stock_number=item['stock_number'], defaults={'name': item['name'], 'model': item['model'], 'amount': item['amount'], 'price': item['price'], 'recommended_price': item['recommended_price'],'weight_class': item['weight_class']})
                        current_item.delivery_store.add(current_customer.unique_vendor_id)
                        current_item.prods.add(current_pr_cat)
                        current_item.save()
                        prod_params, __ = ProductParameters.objects.update_or_create(pr_id=current_item, defaults={
                            'screen_size': item['parameters']['Диагональ (дюйм)'],
                            'dimension': item['parameters']['Разрешение (пикс)'],
                            'RAM': item['parameters']['Встроенная память (Гб)'],
                            'color': item['parameters']['Цвет']})
                        prod_params.save()
                subject = 'Product list imported successfully'
                body = render_to_string('import_export/import.html', {
                    'user': current_customer,
                    'message_body': f'Product list updated. Number of skipped items: {skipped}.'})
                send_mail_async(subject, body, from_email, to)
                return 'OK'
    except ValueError as err:
        subject = 'Product list import failed'
        body = render_to_string('import_export/import.html', {
            'user': current_customer,
            'message_body': 'Product list import failed. Invalid data.'})
        send_mail_async(subject, body, from_email, to)
        return err
