from django.urls import path, include
from rest_framework.routers import DefaultRouter

from backend_code.views import VendorSupply, StoreViewSet, BasketViewSet, StoreCatViewSet, \
    ProductCatViewSet, LoginView, OrderViewSet, OrderDetailViewSet, activate_user, ProductExportViewSet, \
    ProductViewSet, CustomerViewSet, CustomerSignUp

router = DefaultRouter()
router.register(r'goods', ProductViewSet, basename="product-set")
router.register(r'order-detail', OrderDetailViewSet, basename="order-detail-view")

app_name = 'backend_code'
urlpatterns = [
    path('customers/', CustomerViewSet.as_view({'get': 'retrieve', 'delete': 'destroy', 'patch': 'update'}), name='customer-set'),
    # path('products/', ProductView.as_view(), name='product_page'),
    path('goods-import/', VendorSupply.as_view(), name='import_goods_page'),
    # path('product-search/', ProductSearchView.as_view(), name='search_product'),
    path('user-signup/', CustomerSignUp.as_view(), name='user_signup'),
    path('store/', StoreViewSet.as_view({'post': 'create', 'get': 'retrieve', 'delete': 'destroy', 'patch': 'update'}), name='store-set'),
    path('basket/', BasketViewSet.as_view({'post': 'create', 'get': 'list', 'delete': 'destroy'}), name='basket-viewset'),
    path('store-cat/', StoreCatViewSet.as_view({'post': 'create', 'get': 'retrieve', 'delete': 'destroy'}), name='store-cat-view'),
    path('prod-cat/', ProductCatViewSet.as_view({'post': 'create', 'get': 'retrieve', 'delete': 'destroy'}), name='product-cat-view'),
    path('login/', LoginView.as_view(), name='login-view'),
    path('order/', OrderViewSet.as_view({'post': 'create', 'get': 'order_list', 'delete': 'destroy'}), name='order-view'),
    # path('order-detail/<slug:order_slug>/', OrderDetailViewSet.as_view({'get': 'retrieve'}), name='order-detail-view'),
    path('email-activation/<uidb64>/<token>/', activate_user, name='activate-by-mail'),
    path('product-export/', ProductExportViewSet.as_view({'get': 'export_product_list'}), name='export_product_list'),
    path('', include(router.urls)),
]

