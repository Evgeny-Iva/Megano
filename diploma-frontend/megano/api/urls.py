from django.urls import path
from .views import (
    CatalogView,
    CategoryListView,
    PopularProductsView,
)

urlpatterns = [
    # path('banners/', ...),
    path('categories/', CategoryListView.as_view(), name='categories'),
    path('catalog/', CatalogView.as_view(), name='catalog'),
    path('products/popular/', PopularProductsView.as_view(), name='popular-products'),

]