from django.urls import path
from .views import CatalogView, CategoryListView  # ← импорт классов

urlpatterns = [
    # path('banners/', ...),  # пока пропустим
    path('categories/', CategoryListView.as_view(), name='categories'),
    path('catalog/', CatalogView.as_view(), name='catalog'),
]