from django.urls import path
from .views import (
    CatalogView,
    CategoryListView,
    PopularProductsView,
    SalesView,
    BannersView,
    BasketView,
    BasketDeleteView,
)

urlpatterns = [
    path('categories/', CategoryListView.as_view(), name='categories'),
    path('catalog/', CatalogView.as_view(), name='catalog'),
    path('products/popular/', PopularProductsView.as_view(), name='popular-products'),
    path('sales/', SalesView.as_view(), name='sales'),
    path('banners/', BannersView.as_view(), name='banners'),
    path('cart/', BasketView.as_view(), name='cart'),
    path('cart/<int:id>/', BasketDeleteView.as_view(), name='cart-item-delete'),
]