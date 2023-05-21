from django.urls import path

from backend_code.views import VendorSupply, CustomerView, StoreView, BasketView, ProductView, StoreCatView, \
    ProductCatView, LoginView, OrderView, ProductSearchView, OrderDetailView, activate_user, ProductExportView

app_name = 'backend_code'
urlpatterns = [
    path('products/', ProductView.as_view(), name='product_page'),
    path('goods-import/', VendorSupply.as_view(), name='import_goods_page'),
    path('product-search/', ProductSearchView.as_view(), name='search_product'),
    path('user/', CustomerView.as_view(), name='user-view'),
    path('store/', StoreView.as_view(), name='store-create'),
    path('basket/', BasketView.as_view(), name='basket-view'),
    path('store-cat/', StoreCatView.as_view(), name='store-cat-view'),
    path('prod-cat/', ProductCatView.as_view(), name='product-cat-view'),
    path('login/', LoginView.as_view(), name='login-view'),
    path('order/', OrderView.as_view(), name='order-view'),
    path('order-detail/', OrderDetailView.as_view(), name='order-detail-view'),
    path('email-activation/<uidb64>/<token>/', activate_user, name='activate-by-mail'),
    path('product-export/', ProductExportView.as_view(), name='export_product_list'),
]

