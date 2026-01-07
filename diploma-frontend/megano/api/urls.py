from django.urls import path
from .views import (
    CatalogView,
    CategoryListView,
    PopularProductsView,
    SalesView,
    BannersView,
)

urlpatterns = [
    path('categories/', CategoryListView.as_view(), name='categories'),
    path('catalog/', CatalogView.as_view(), name='catalog'),
    path('products/popular/', PopularProductsView.as_view(), name='popular-products'),
    path('sales/', SalesView.as_view(), name='sales'),
    path('banners/', BannersView.as_view(), name='banners'),
]