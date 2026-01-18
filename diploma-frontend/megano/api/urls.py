from django.urls import path
from .views import (
    CatalogView,
    CategoryListView,
    PopularProductsView,
    SalesView,
    BannersView,
    BasketView,
    BasketDeleteView,
    SignInView,
    SignUpView,
    SignOutView,
    OrderCreateView,
    OrderDetailView,
    PaymentView,
)

urlpatterns = [
    path('sing-in/', SignInView.as_view(), name='sing-in'),
    path('sing-up/', SignUpView.as_view(), name='sing-up'),
    path('sing-out/', SignOutView.as_view(), name='sing-out'),
    path('categories/', CategoryListView.as_view(), name='categories'),
    path('catalog/', CatalogView.as_view(), name='catalog'),
    path('sales/', SalesView.as_view(), name='sales'),
    path('banners/', BannersView.as_view(), name='banners'),
    path('cart/', BasketView.as_view(), name='cart'),
    path('orders/', OrderCreateView.as_view(), name='order-create'),
    path('payment/', PaymentView.as_view(), name='payment'),
    path('products/popular/', PopularProductsView.as_view(), name='popular-products'),
    path('cart/<int:id>/', BasketDeleteView.as_view(), name='cart-item-delete'),
    path('orders/<int:id>/', OrderDetailView.as_view(), name='order-detail'),
]