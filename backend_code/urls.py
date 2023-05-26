from django.urls import path, include
from rest_framework.routers import DefaultRouter

from backend_code.views import VendorSupply, CustomerView, StoreView, BasketView, StoreCatView, \
    ProductCatView, LoginView, OrderView, OrderDetailView, activate_user, ProductExportView, \
    ProductViewSet, CustomerViewSet


router = DefaultRouter()
router.register(r'goods', ProductViewSet, basename="product-set")
# router.register(r'customers', CustomerViewSet.as_view({'get': 'retrieve', 'delete': 'destroy'}), basename="customer-set")


app_name = 'backend_code'
urlpatterns = [
    path('customers/', CustomerViewSet.as_view({'get': 'retrieve', 'delete': 'destroy'}), name='customer-set'),
    # path('products/', ProductView.as_view(), name='product_page'),
    path('goods-import/', VendorSupply.as_view(), name='import_goods_page'),
    # path('product-search/', ProductSearchView.as_view(), name='search_product'),
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
    path('', include(router.urls)),
]

