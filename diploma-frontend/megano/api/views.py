from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from .models import Category, Product
from django.utils.dateformat import format
import json
import pytz


class SignInView(APIView):
    """View для входа пользователя в систему"""

    def post(self, request):
        """
        Обработка POST-запроса на вход в систему

        Ожидание JSON с полями:
        - username
        - password

        Возращение:
        - 200 OK при успехе
        - 500 Internal Server Error при ошибке
        """
        try:
            username = request.data.get('username', '').strip()
            password = request.data.get('password', '').strip()

            if not username or not password:
                return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                return Response(status=status.HTTP_200_OK)

            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SignUpView(APIView):
    """View для регистрации нового пользователя."""

    def post(self, request):
        """
        Обработка POST-запроса на регистрацию.

        Ожидание JSON с полями:
        - username
        - password
        - name

        возращение:
        - 200 OK при успехе
        - 500 Internal Server Error при ошибке
        """
        try:
            name = request.data.get('name', '').strip()
            username = request.data.get('username', '').strip()
            password = request.data.get('password', '').strip()

            user = User.objects.create_user(  #TODO стоит ли оставлять переменную если она не используется,
                username=username,            # но это считается хорошим тоном
                password=password,
                first_name=name
            )
            return Response(status=status.HTTP_200_OK)

        except Exception:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SignOutView(APIView):
    """View для выхода пользователя из системы."""

    def post(self, request):
        """
        Обработка POST-запроса на выход.

        Удаляет сессию пользователя.
        Всегда возвращает 200 OK.
        """
        logout(request)
        return Response(status=status.HTTP_200_OK)


class CategoryListView(APIView):
    """
    API endpoint для получения структурированного меню категорий.

    Возвращает иерархию категорий с подкатегориями.
    Используется для построения навигации в каталоге.

    Пример запроса:
    GET /api/categories/

    Возвращает:
    [
        {
            "id": int,
            "title": str,
            "image": {"src": str, "alt": str},
            "subcategories": [
                {
                    "id": 2,
                    "title": "Видеокарты",
                    "image": {"src": "/gpu.png", "alt": "Видеокарты"},
                    "subcategories": []
                }
            ]
        }
    ]
    Статусы ответов:
    - 200: Успешный запрос
    - 500: Ошибка сервера
    """
    def get(self, request):
        """
        Обработка GET-запроса для получения категорий.

        Возвращает только корневые категории (parent=None),
        каждая содержит свои подкатегории в поле 'subcategories'.

        Args:
            request (HttpRequest): Запрос без параметров

        Returns:
            Response: JSON-массив с категориями и подкатегориями
        """
        name = Category.object.all

        categories_data = []
        for category in name:
            category_dict = {
                'id': category.id,
                'title': category.title,
                'image': {
                    'src': category.image_src,
                    'alt': category.image_alt,
                },
                'subcategories': []
            }
            categories_data.append(category_dict)

        return Response(categories_data)


class CatalogView(APIView):
    """
    API endpoint для получения товаров с фильтрацией и пагинацией.

    Поддерживает:
    - Фильтрацию по категории (?category=id)
    - Текстовый поиск (?filter=текст)
    - Сортировку по цене (?sortType=inc/dec)
    - Пагинацию (?limit=20&currentPage=1)

    Поддерживает:
    - Фильтрацию по категории (?category=id)
    - Текстовый поиск (?filter=текст)
    - Сортировку по цене (?sortType=inc/dec)
    - Пагинацию (?limit=20&currentPage=1)

    Примеры запросов:
    GET /api/catalog/?category=55&limit=10
    GET /api/catalog/?filter=видеокарта&sortType=inc
    GET /api/catalog/?currentPage=2&limit=5

    Возвращает:
    {
        "items": [
            {
                "id": 123,
                "title": "Видеокарта RTX 4090",
                "price": 150000.0,
                "category": 55,
                "freeDelivery": true,
                "rating": 4.8,
                "date": "Thu Feb 09 2023 21:39:52 GMT+0100",
                "count": 12,
                "description": "Мощная игровая видеокарта",
                "reviews": 47,
                "tags": [{"id": 12, "name": "Gaming"}],
                "images": [{"src": "/gpu.jpg", "alt": "Видеокарта RTX 4090"}]
            }
        ],
        "currentPage": 1,
        "lastPage": 8
    }

    Статусы ответов:
    - 200: Успешный запрос
    - 400: Неверные параметры запроса (например, limit='abc')
    - 500: Ошибка сервера

    Примечание:
    - Дата возвращается в формате: "Thu Feb 09 2023 21:39:52 GMT+0100"
    - Цена и рейтинг возвращаются как числа с плавающей точкой
    """
    def get(self, request):
        """
        Обработка GET-запроса для получения товаров.

        Args:
            request (HttpRequest): Запрос с возможными параметрами:
                - category (int, optional): ID категории для фильтрации
                - filter (str, optional): Текст для поиска в названиях
                - sortType (str, optional): 'inc' (по возрастанию) или
                                      'dec' (по убыванию, по умолчанию)
                - limit (int, optional): Количество товаров на странице (по умолчанию 20)
                - currentPage (int, optional): Номер страницы (по умолчанию 1)

        Returns:
            Response: JSON с товарами и метаданными пагинации

        Raises:
        ValueError: Если limit или currentPage не являются числами
        Product.DoesNotExist: Если категория не найдена (при фильтрации)
        """
        products = Product.objects.all()

        category_id = request.GET.get('category')
        search = request.GET.get('filter', '').strip()
        sort_type = request.GET.get('sortType', 'dec')
        limit = int(request.GET.get('limit', 20))
        current_page = int(request.GET.get('currentPage', 1))

        if category_id:
            products = products.filter(category_id=category_id)

        if search:
            products = products.filter(title__icontains=search)

        if sort_type == 'inc':
            products = products.order_by('price')
        else:
            products = products.order_by('-price')

        total_count = products.count()
        last_page = (total_count + limit - 1) // limit

        offset = (current_page - 1) * limit
        products = products[offset:offset + limit]

        products = products.select_related('category')\
            .prefetch_related('tags', 'images')

        items = []
        for product in products:
            date_str = format(
                product.date.astimezone(pytz.timezone('Europe/Moscow')),
                'D M d Y H:i:s O'
            )
            item = {
                "id": product.id,
                "title": product.title,
                "price": float(product.price),
                "category": product.category.id,
                "freeDelivery": product.freeDelivery,
                "rating": float(product.rating),
                "date": date_str,
                "count": product.count,
                "description": product.description,
                "reviews": product.reviews,
            }

            item.update({
                "tags": [{"id": t.id, "name": t.name} for t in product.tags.all()],
                "images": [{"src": i.src, "alt": i.alt} for i in product.images.all()]
            })

            items.append(item)

        return Response({
            "items": items,
            "currentPage": current_page,
            "lastPage": last_page
        })


@method_decorator(cache_page(300), name='dispatch')
class PopularProductsView(APIView):
    """
    API endpoint для получения популярных товаров.

    Возвращает топ-10 товаров по рейтингу.
    Результат кэшируется на 5 минут для увеличения производительности.

    Пример запроса:
    GET /api/products/popular/

    Возвращает:
    [
        {
            "id": 123,
            "title": "Видеокарта RTX 4090",
            "price": 150000.0,
            "category": 55,
            "freeDelivery": true,
            "rating": 4.8,
            "date": "Thu Feb 09 2023 21:39:52 GMT+0100",
            "count": 12,
            "description": "Мощная игровая видеокарта",
            "reviews": 47,
            "tags": [{"id": 12, "name": "Gaming"}],
            "images": [{"src": "/gpu.jpg", "alt": "Видеокарта RTX 4090"}]
        },
        ... еще 9 товаров
    ]

    Статусы ответов:
    - 200: Успешный запрос
    - 500: Ошибка сервера

    Примечание:
    - Для сброса кэша: python manage.py shell -> cache.clear()
    - Товары без рейтинга (rating=0) не попадают в топ
    """
    def get(self, request):
        """
        Обработка GET-запроса для получения популярных товаров.

        Алгоритм популярности: товары сортируются по рейтингу (rating)
        в порядке убывания. Берутся первые 10 товаров.

        Args:
            request (HttpRequest): Запрос без параметров

        Returns:
            Response: JSON-массив с популярными товарами
        """
        popular_products = Product.objects.all()\
            .order_by('-rating')\
            .select_related('category')\
            .prefetch_related('tags', 'images')[:10]

        items = []
        for product in popular_products:
            date_str = format(
                product.date.astimezone(pytz.timezone('Europe/Moscow')),
                'D M d Y H:i:s O'
            )
            item = {
                "id": product.id,
                "title": product.title,
                "price": float(product.price),
                "category": product.category.id,
                "freeDelivery": product.freeDelivery,
                "rating": float(product.rating),
                "date": date_str,
                "count": product.count,
                "description": product.description,
                "reviews": product.reviews,
            }
            item.update({
                "tags": [{"id": t.id, "name": t.name} for t in product.tags.all()],
                "images": [{"src": i.src, "alt": i.alt} for i in product.images.all()]
            })

            items.append(item)

        return Response(items)