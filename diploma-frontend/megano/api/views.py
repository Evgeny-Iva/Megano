import logging
import json
import pytz

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.utils.dateformat import format
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.utils import timezone
from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework.authtoken.models import Token
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from datetime import datetime

from .models import Basket, Category, Product, Sale, Order, Profile, Tag, OrderItem
from .serializers import (
    AddToBasketSerializer,
    BasketResponseSerializer,
    CreateOrderSerializer,
    OrderSerializer,
    PaymentSerializer,
    ProfileSerializer,
    ChangePasswordSerializer,
    AvatarUpdateSerializer,
    TagSerializer,
    ProductDetailSerializer,
    CreateReviewSerializer,
)
from .services.order_service import OrderService


logger = logging.getLogger(__name__)

class PaginatorHelper:
    """
    Вспомогательный класс для пагинации в API endpoints.

    Использование:
        helper = PaginatorHelper(request)
        limit, current_page = helper.get_validated_params()
        offset = helper.calculate_offset()
        last_page = helper.calculate_last_page(total_count)
    """

    def __init__(self, request, default_limit=20, max_limit=100):
        self.request = request
        self.default_limit = default_limit
        self.max_limit = max_limit
        self.original_limit = request.GET.get('limit')
        self.original_page = request.GET.get('currentPage')

    def get_validated_params(self):
        """
        Возвращает валидные limit и current_page с логированием.
        """
        limit = self._validate_limit()
        current_page = self._validate_page()
        return limit, current_page

    def _validate_limit(self):
        """Валидация параметра limit"""
        if self.original_limit is None:
            return self.default_limit

        try:
            limit = int(self.original_limit)
            if limit <= 0:
                logger.warning(f"Слишком маленький limit: {self.original_limit}")
                return self.default_limit
            elif limit > self.max_limit:
                logger.info(f"Большой limit: {self.original_limit}")
                return self.max_limit
            return limit
        except (ValueError, TypeError):
            logger.warning(f"Некорректный limit: {self.original_limit}")
            return self.default_limit

    def _validate_page(self):
        """Валидация параметра currentPage"""
        if self.original_page is None:
            return 1

        try:
            current_page = int(self.original_page)
            if current_page <= 0:
                logger.warning(f"Некорректная страница: {self.original_page}")
                return 1
            return current_page
        except (ValueError, TypeError):
            logger.warning(f"Некорректный currentPage: {self.original_page}")
            return 1

    def calculate_offset(self, current_page, limit):
        """Вычисляет offset для пагинации"""
        return (current_page - 1) * limit

    def calculate_last_page(self, total_count, limit):
        """Вычисляет общее количество страниц"""
        if total_count == 0:
            return 1
        return (total_count + limit - 1) // limit  # округление вверх

    def adjust_current_page(self, current_page, last_page):
        """
        Корректирует current_page если она больше last_page.
        Возвращает скорректированную страницу.
        """
        if current_page > last_page and last_page > 0:
            logger.info(
                f"Запрошена несуществующая страница: {current_page}, "
                f"всего страниц: {last_page}"
            )
            return last_page
        return current_page


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
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        try:
            if 'application/json' in request.content_type:
                username = request.data.get('username', '').strip()
                password = request.data.get('password', '').strip()

            else:
                username = request.POST.get('username', '').strip()
                password = request.POST.get('password', '').strip()

                if not username and not password:
                    try:
                        for key in request.POST.keys():
                            data = json.loads(key)
                            username = data.get('username', '').strip()
                            password = data.get('password', '').strip()
                            if username or password:
                                break
                    except:
                        pass

            print(f"DEBUG: Username='{username}', Password='{password}'")

            if not username or not password:
                return Response(  # ← ДОБАВЬТЕ return
                    {'error': 'Username and password are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)

                return Response({
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'fullName': user.get_full_name() or user.username,
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response(
                    {'error': 'Invalid username or password'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

        except Exception as e:
            print(f"ERROR: {e}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
            raw = list(request.data.keys())[0] if request.data else '{}'
            try:
                data = json.loads(raw)
            except:
                return Response({'error': 'Invalid JSON'}, status=400)

            name = data.get('name', '').strip()
            username = data.get('username', '').strip()
            password = data.get('password', '').strip()

            print(f"Используем: name='{name}', username='{username}'")

            logger.info(f"SignUp attempt: name={name}, username={username}")


            if not username:
                logger.warning("Missing username")
                return Response(
                    {'error': 'Username are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not password:
                logger.warning("Missing password")
                return Response(
                    {'error': 'Password are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if User.objects.filter(username=username).exists():
                logger.warning(f"User {username} already exists")
                return Response(
                    {'error': 'Username already exists'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user = User.objects.create_user(
                username=username,
                password=password,
                first_name=name
            )

            logger.info(f"User created: {user.id}")
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

        request.session.flush()

        response = Response(
            {'message': 'Logged out successfully'},
            status=status.HTTP_200_OK
        )

        response.delete_cookie('sessionid')

        return response


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
        name = Category.objects.all()

        categories_data = []
        for category in name:
            category_dict = {
                'id': category.id,
                'title': category.title,
                'image': {
                    'src': category.src,
                    'alt': category.alt,
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

        Особенности:
            - Параметры limit и currentPage автоматически корректируются при ошибках
            - Несуществующая категория приводит к пустому результату (без ошибки)
        """

        paginator = PaginatorHelper(request)
        limit, current_page = paginator.get_validated_params()
        products = Product.objects.all()

        category_id = request.GET.get('category')
        search = request.GET.get('filter', '').strip()
        sort_type = request.GET.get('sortType', 'dec')

        if category_id:
            products = products.filter(category_id=category_id)

        if search:
            products = products.filter(title__icontains=search)

        if sort_type == 'inc':
            products = products.order_by('price')
        else:
            products = products.order_by('-price')

        total_count = products.count()
        last_page = paginator.calculate_last_page(total_count, limit)

        if current_page > last_page:
            return Response({
                "items": [],
                "currentPage": current_page,
                "lastPage": last_page
            })

        offset = paginator.calculate_offset(current_page, limit)
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
                "freeDelivery": product.free_delivery,
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
                "freeDelivery": product.free_delivery,
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


class SalesView(APIView):
    """
    API endpoint для получения товаров со скидкой и пагинацией.

    Возвращает пагинированный список товаров, на которые действует скидка
    в текущий день. Скидка считается активной, если текущая дата находится
    между date_from и date_to включительно.

    Поддерживает пагинацию через параметры:
        - limit (int, optional): Количество товаров на странице (по умолчанию 10)
        - currentPage (int, optional): Номер текущей страницы (по умолчанию 1)

    Пример запроса:
    GET /api/sales/?limit=10&currentPage=2

    Возвращает:
    {
        "items": [
            {
                "id": 123
                "title": "Видеокарта RTX 4090",
                "price": 150000.0,
                "dateTo": ,
                "dateFrom": ,
                "salePrice": 10,
                "images": [
                    {
                        "src": "/gpu.jpg",
                        "alt": "Видеокарта RTX 4090"
                    }
                ]
            }
        ],
        "currentPage": 1,
        "lastPage": 8
    }

    Статусы ответов:
        - 200: Успешный запрос
        - 400: Неверные параметры (например, limit='abc')

    Примечания:
        - Поля dateFrom и dateTo возвращаются в формате MM-DD
        - Если товар не имеет изображений, поле images содержит пустой массив
        - Если запрошена несуществующая страница, возвращается пустой массив items
        - ID в ответе — это ID товара (Product), а не скидки (Sale)
    """

    def get(self, request):
        """
        Обработка GET-запроса для получения товаров со скидкой.

        Args:
            request (HttpRequest): Объект запроса с опциональными параметрами:
                - limit (str): Количество товаров на странице (по умолчанию "20")
                - currentPage (str): Номер текущей страницы (по умолчанию "1")

        Returns:
            Response: JSON-ответ с товарами и метаданными пагинации.

        Notes:
            - Некорректные параметры автоматически корректируются
            - Если запрошена несуществующая страница, возвращается пустой items
            - Если нет активных скидок, items будет пустым массивом
        """

        paginator = PaginatorHelper(request)
        limit, current_page = paginator.get_validated_params()

        active_sales = Sale.objects.get_active()

        total_count = active_sales.count()
        last_page = paginator.calculate_last_page(total_count, limit)
        current_page = paginator.adjust_current_page(current_page, last_page)

        if current_page > last_page:
            return Response({
                "items": [],
                "currentPage": current_page,
                "lastPage": last_page
            })

        offset = paginator.calculate_offset(current_page, limit)
        paginated_sales = active_sales[offset:offset + limit]

        paginated_sales = paginated_sales.select_related('product')

        items = []
        for sale in paginated_sales:
            product = sale.product

            item = {
                "id": sale.product.id,
                "title": product.title,
                "price": float(product.price),
                "dateTo": sale.date_to.strftime('%m-%d'),
                "dateFrom": sale.date_from.strftime('%m-%d'),
                "salePrice": float(sale.sale_price),
            }
            item.update({
                "images": [
                    {"src": i.src, "alt": i.alt}
                    for i in product.images.all()[:1]
                ]
            })
            items.append(item)

        return Response({
            "items": items,
            "currentPage": current_page,
            "lastPage": last_page
        })


@method_decorator(cache_page(300), name='dispatch')
class BannersView(APIView):
    """
    API endpoint для получения баннеров для главной страницы.

    Баннеры — это специально отобранные товары для показа на главной странице.
    В текущей реализации возвращаются 5 товаров с наивысшим рейтингом.

    Пример запроса:
    GET /api/banners/

    Возвращает:
    [
        {
            "id": 123,
            "category": 55,
            "price": 500.67,
            "count": 12,
            "date": "Thu Feb 09 2023 21:39:52 GMT+0100",
            "title": "video card",
            "description": "description of the product",
            "freeDelivery": true,
            "images": [
                {
                "src": "/3.png",
                "alt": "Image alt string"
                }
            ],
            "tags": [
                {
                "id": 12,
                "name": "Gaming"
                }
            ],
            "reviews": 5,
            "rating": 4.6
        },
    ]

    Особенности:
        - Возвращает 5 товаров с наивысшим рейтингом
        - Данные кэшируются на 5 минут для производительности
        - Формат даты соответствует JavaScript Date toString()
    """

    def get(self, request):
        """
        Обработка GET-запроса для получения баннеров.

        Возвращает 5 товаров с наивысшим рейтингом.
        Выборка закеширована для повышения производительности.

        Returns:
            Response: JSON-массив товаров в формате баннеров.
        """

        banner_products = Product.objects.all()\
            .order_by('-rating')\
            .select_related('category')\
            .prefetch_related('tags', 'images')[:5]

        banners_data = []
        for product in banner_products:
            date_str = format(
                product.date.astimezone(pytz.timezone('Europe/Moscow')),
                'D M d Y H:i:s O'
            )
            banner = {
                "id": product.id,
                "title": product.title,
                "price": float(product.price),
                "category": product.category.id,
                "freeDelivery": product.free_delivery,
                "rating": float(product.rating),
                "date": date_str,
                "count": product.count,
                "description": product.description,
                "reviews": product.reviews,
            }

            first_image = product.images.first()
            if first_image:
                banner["images"] = [{
                    "src": first_image.src,
                    "alt": first_image.alt
                }]
            else:
                banner["images"] = []

            banner["tags"] = [
                {"id": tag.id, "name": tag.name}
                for tag in product.tags.all()
            ]

            banners_data.append(banner)

        return Response(banners_data)


class BasketView(APIView):
    """
    API endpoint для управления корзиной пользователя.

    Пример запроса:
        GET    /api/basket/ - Получить содержимое корзины
        POST   /api/basket/ - Добавить товар в корзину

    Требует аутентификации.

    Возвращает:
        {
            "items": [
                {
                    "id": 123,
                    "category": 55,
                    "price": 500.67,
                    "count": 3,
                    "date": "Thu Feb 09 2023 21:39:52 GMT+0100",
                    "title": "video card",
                    "description": "description of the product",
                    "freeDelivery": true,
                    "images": [
                        {
                            "src": "/3.png",
                            "alt": "Image alt string"
                        }
                    ],
                    "tags": [
                        {
                            "id": 12,
                            "name": "Gaming"
                        }
                    ],
                    "reviews": 5,
                    "rating": 4.6
                }
            ],
            "totalCount": 5,
            "totalPrice": 2500.35
        }

    Возвращает:
        {
            "id": 123,
            "count": 2
        }

    Возвращает:
        {
            "id": 123,
            "count": 3
        }

    Статусы ответов:
        - 200: Успешно (GET или обновление существующего товара)
        - 201: Товар добавлен в корзину (POST для нового товара)
        - 400: Ошибка валидации (неверные данные)
        - 401: Не авторизован
        - 404: Товар не найден
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """
        GET /api/basket/ - Получить все товары в корзине.

        Возвращает список товаров в корзине пользователя с подсчётом итогов.
        Каждый товар содержит полную информацию + поле 'count' (количество в корзине).

        Returns:
            Response: JSON с товарами и summary.
        """

        basket_items = Basket.objects.filter(user=request.user)\
            .select_related('product', 'product__category')\
            .prefetch_related('product__images', 'product__tags')

        serializer = BasketResponseSerializer(basket_items, many=True)

        total_count = basket_items.aggregate(total=Sum('quantity'))['total'] or 0
        total_price = sum(item.total_price for item in basket_items)

        return Response(serializer.data)

    def post(self, request):
        """
        POST /api/basket/ - Добавить товар в корзину.

        Добавляет товар в корзину. Если товар уже есть в корзине - увеличивает количество.
        Проверяет доступность товара на складе.

        Args:
            request.data должна содержать:
                - id (int): ID товара (обязательно)
                - count (int): количество (по умолчанию 1, минимум 1)

        Returns:
            Response: JSON с id товара и новым количеством в корзине.

        Raises:
            ValidationError: Если товар не найден или недостаточно на складе.
        """

        serializer = AddToBasketSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product = serializer.validated_data['product']
        count = serializer.validated_data['count']

        basket_item, created = Basket.objects.get_or_create(
            user=request.user,
            product=product,
            defaults={'quantity': count}
        )

        if not created:
            basket_item.quantity += count
            basket_item.save()

        baskets = Basket.objects.filter(user=request.user) \
            .select_related('product', 'product__category') \
            .prefetch_related('product__images', 'product__tags')

        serializer = BasketResponseSerializer(baskets, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request):
        """Удаление товара из корзины"""
        try:
            data = json.loads(request.body)
            product_id = data.get('id')
            count = data.get('count', None)
        except Exception as e:
            return Response({"error": f"Invalid data: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            basket_item = Basket.objects.get(user=request.user, product_id=product_id)

            if count is None or  count >= basket_item.quantity:
                basket_item.delete()
            else:
                basket_item.quantity -= count
                basket_item.save()

            basket = Basket.objects.filter(user=request.user) \
                .select_related('product', 'product__category') \
                .prefetch_related('product__images', 'product__tags')

            serializer = BasketResponseSerializer(basket, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Basket.DoesNotExist:
            return Response({"error": "Product not in basket"}, status=status.HTTP_404_NOT_FOUND)


class BasketDeleteView(APIView): #TODO обрати внимание!!!
    """
    API endpoint для удаления товаров из корзины.

    Пример запроса:
        DELETE /api/basket/ - Очистить корзину
        DELETE /api/basket/{id}/ - Удалить конкретный товар

    Требует аутентификации.

    Пример DELETE /api/basket/ (очистка корзины):
        Response:
            {
                "deleted": 5
            }

    Пример DELETE /api/basket/123/ (удаление товара):
        Response: 204 No Content

    Статусы ответов:
        - 204: Успешно удалено
        - 401: Не авторизован
        - 404: Товар не найден в корзине
    """

    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, id=None):
        """
        DELETE /api/basket/ или /api/basket/{id}/ - Удалить товар(ы) из корзины.

        Если id не указан: удаляет все товары из корзины пользователя.
        Если id указан: удаляет конкретный товар из корзины.

        Args:
            id (int, optional): ID товара для удаления. Если None - очистить корзину.

        Returns:
            Response: Для очистки корзины - JSON с количеством удалённых товаров.
                     Для удаления товара - 204 No Content.

        Raises:
            Http404: Если товар не найден в корзине (при удалении по id).
        """

        if id is None:
            deleted_count, _ = Basket.objects.filter(user=request.user).delete()
            return Response(
                {"deleted": deleted_count},
                status=status.HTTP_204_NO_CONTENT
            )

        try:
            basket_item = Basket.objects.get(user=request.user, product_id=id)
            basket_item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Basket.DoesNotExist:
            return Response(
                {"error": "Product not found in basket"},
                status=status.HTTP_404_NOT_FOUND
            )


class OrderCreateView(APIView):
    """
    API endpoint для создания заказов

    Endpoint:
        - POST /api/orders/  - создание нового заказа
        - GET  /api/orders/  - получение активного заказа

    Описание:
    Создает новый заказ на основе товаров в корзине пользователя.
    После успешного создания заказа корзина очищается.

    Требования:
        - Пользователь должен быть авторизован
        - Корзина не должна быть пустой
        - Все обязательные поля должны быть заполнены

    ==================== POST /api/orders/ ====================

    Request Body (тело запроса):
    {
        "fullName": "Иван Иванов",
        "email": "ivan@example.com",
        "phone": "+79991234567",
        "deliveryType": "ordinary",
        "paymentType": "online",
        "city": "Москва",
        "address": "ул. Примерная, 1"
    }

    Response (Успешно - 200 OK):
    {
        "orderId": 1,
        "totalCost": "2500.00",
        "deliveryPrice": "0.00",
        "status": "accepted"
    }

    Response (Ошибка - 400 Bad Request):
    {
        "error": "Корзина пуста"
    }

    ==================== GET /api/orders/ ====================

    Response (Успешно - 200 OK):
    {
        "id": 123,
        "createdAt": "2023-05-05 12:12",
        "fullName": "Amoying Orange",
        "email": "no-reply@mail.ru",
        "phone": "88888888888",
        "deliveryType": "free",
        "paymentType": "online",
        "totalCost": 567.8,
        "status": "accepted",
        "city": "Moscow",
        "address": "red square 1",
        "products": [
            {
                "id": 123,
                "category": 55,
                "price": 500.67,
                "count": 12,
                "date": "Thu Feb 09 2023 21:39:52 GMT+0100",
                "title": "video card",
                "description": "description of the product",
                "freeDelivery": true,
                "images": [
                    {
                        "src": "/3.png",
                        "alt": "Image alt string"
                    }
                ]
            }
        ]
    }

        Response (Нет активного заказа - 200 OK):
    {}

    Статусы ответов:
        200 - Успешный GET или POST запрос
        400 - Неверные данные или пустая корзина
        401 - Пользователь не авторизован

    Логика работы (POST):
        1. Валидация входных данных через сериализатор
        2. Передача данных в сервисный слой
        3. Обработка бизнес-логики в сервисе
        4. Возврат результата клиенту

        Логика работы (GET):
        1. Поиск активного заказа пользователя
        2. Сериализация данных заказа
        3. Возврат результата клиенту
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """GET /orders - получить активный заказ"""

        active_order = Order.objects.filter(
            user=request.user
        ).order_by('-created_at').first()

        if not active_order:
            return Response({}, status=200)

        serializer = OrderSerializer(active_order)
        return Response(serializer.data, status=200)

    def post(self, request):
        """POST /api/orders/ - создать новый заказ"""

        basket_items = Basket.objects.filter(user=request.user)

        if not basket_items.exists():
            return Response({'error': 'Корзина пуста'}, status=400)

        profile = request.user.profile

        delivery_type = request.POST.get('deliveryType', 'free') if hasattr(request, 'POST') else 'free'
        payment_type = request.POST.get('paymentType', 'online') if hasattr(request, 'POST') else 'online'
        city = request.POST.get('city', 'Не указан') #TODO переделать нормально
        address = request.POST.get('address', 'Не указан')

        order_data = {
            'full_name': profile.fullName,
            'email': request.user.email,
            'phone': profile.phone,
            'delivery_type': delivery_type,
            'payment_type': payment_type,
            'city': city,
            'address': address,
        }

        serialize = CreateOrderSerializer(data=order_data)
        serialize.is_valid(raise_exception=True)

        order = Order.objects.create(
            user=request.user,
            full_name=serialize.validated_data['full_name'],
            email=serialize.validated_data['email'],
            phone=serialize.validated_data['phone'],
            delivery_type=serialize.validated_data['delivery_type'],
            payment_type=serialize.validated_data['payment_type'],
            city=serialize.validated_data['city'],
            address=serialize.validated_data['address'],
            total_cost=sum(item.product.price * item.quantity for item in basket_items)
        )

        for basket in basket_items:
            OrderItem.objects.create(
                order=order,
                product=basket.product,
                quantity=basket.quantity,
                price=basket.product.price
            )

        basket_items.delete()

        return Response({
            'orderId': order.id,
            'totalCost': str(order.total_cost),
            'status': order.status
        })


class OrderDetailView(APIView):
    """
    API endpoint для работы с конкретным заказом

    Endpoints:
    - GET  /orders/{id}/  - получение информации о заказе
    - POST /orders/{id}/  - подтверждение заказа (изменение статуса)

    Описание:
    GET: Возвращает полную информацию о заказе
    POST: Подтверждает заказ - меняет статус на 'confirmed' или 'paid'

    Response (200 OK):
    {
        "id": 123,
        "createdAt": "2023-05-05 12:12",
        "fullName": "Amoying Orange",
        "email": "no-reply@mail.ru",
        "phone": "88888888888",
        "deliveryType": "free",
        "paymentType": "online",
        "totalCost": 567.8,
        "status": "accepted",
        "city": "Moscow",
        "address": "red square 1",
        "products": [...]
    }

    Response (404 Not Found):
    {
        "error": "Заказ не найден"
    }

    Status Codes:
        200 - Заказ найден
        401 - Пользователь не авторизован
        403 - Заказ принадлежит другому пользователю
        404 - Заказ не найден
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, id):
        """GET /orders/{id} - получить заказ по ID"""
        try:
            order = Order.objects.get(id=id)

            if order.user != request.user:
                return Response(
                    {"error": "Доступ запрещен"},
                    status=status.HTTP_403_FORBIDDEN
                )

            serializer = OrderSerializer(order)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Order.DoesNotExist:
            return Response(
                {"error": "Заказ не найден"},
                status=status.HTTP_404_NOT_FOUND
            )

    def post(self, request, id):
        """POST /orders/{id}/ - подтвердить заказ"""
        try:
            order = Order.objects.get(id=id, user=request.user)

            if order.status not in ['accepted', 'pending']:
                return Response(
                    {"error": f"Заказ уже в статусе '{order.status}'"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            order.status = 'confirmed'
            order.save()

            return Response({
                "orderId": order.id,
                "confirmed": True,
                "status": order.status
            }, status=status.HTTP_200_OK)

        except Order.DoesNotExist:
            return Response(
                {"error": "Заказ не найден"},
                status=status.HTTP_404_NOT_FOUND
            )


class PaymentView(APIView):
    """
    API endpoint для оплаты заказа

    Endpoint: POST /payment/{id}/

    Описание:
    Принимает данные банковской карты и обрабатывает оплату заказа.
    После успешной оплаты меняет статус заказа.

    Request Body:
    {
        "number": "99999999999999",
        "name": "Annoying Orange",
        "month": "02",
        "year": "2025",
        "code": "123"
    }

    Response (200 OK):
    {
        "success": true,
        "orderId": 123,
        "message": "Оплата успешно проведена"
    }

    Response (400 Bad Request):
    {
        "error": "Неверные данные карты"
    }

    Response (404 Not Found):
    {
        "error": "Заказ не найден"
    }
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id):
        """POST /payment/{id}/ - оплатить заказ"""

        try:
            order = Order.objects.get(id=id, user=request.user)

            data = request.data
            errors = {}

            number = data.get('number', data.get('number1', ''))
            cleaned_number = number.replace(' ', '').replace('-', '')

            if not cleaned_number.isdigit() or len(number) != 16:
                errors['number'] = 'Номер карты должен содержать 16 цифр'

            name = data.get('name', '')
            if len(name.strip()) < 3:
                errors['name'] = 'Введите имя владельца карты'

            month = data.get('month', '')
            if not month.isdigit() or int(month) < 1 or int(month) > 12:
                errors['month'] = 'Месяц должен быть от 01 до 12'

            year = data.get('year', '')
            if not year.isdigit() or len(year) != 2:
                errors['year'] = 'Год должен содержать 2 цифры'
            else:
                current_year = datetime.now().year
                print(f"Current year: {current_year}")

                if len(year) == 2:
                    year_num = 2000 + int(year)
                else:
                    year_num = int(year)

                print(f"Card year: {year_num}")

                if year_num < current_year:
                    errors['year'] = 'Срок действия карты истек'
                else:
                    print("Year validation passed")

            code = data.get('code', '')
            if not code.isdigit() or len(code) != 3:
                errors['code'] = 'CVV код должен содержать 3 цифры'

            if errors:
                return Response(errors, status=400)

            order.status = 'paid'
            order.save()

            return Response({
                'success': True,
                'orderId': order.id,
                'status': order.status
            })

        except Order.DoesNotExist:
            return Response(
                {"error": "Заказ не найден"},
                status=status.HTTP_404_NOT_FOUND
            )


class ProfileView(APIView):
    """
    API endpoint для работы с профилем

    Endpoints:
    GET  /api/profile/  - получить профиль
    POST /api/profile/  - обновить профиль

    Response (200 OK):
    {
        "fullName": "Иван Иванов",
        "email": "ivan@example.com",
        "phone": "+79991234567",
        "avatar": "/media/avatars/user123.jpg"
    }
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """GET /profile/ - получить профиль пользователя"""
        try:
            profile = Profile.objects.select_related(
                'user', 'avatar'
            ).get(user=request.user)
            serializer = ProfileSerializer(profile)
        except Profile.DoesNotExist:
            return Response({
                "fullName": request.user.get_full_name() or request.user.username,
                "email": request.user.email,
                "phone": "",
                "avatar": None
            }, status=status.HTTP_200_OK)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """POST /api/profile/ - обновить профиль"""
        serializer = ProfileSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        user = request.user

        try:
            profile = Profile.objects.get(user=user)
        except Profile.DoesNotExist:
            profile = Profile.objects.create(
                user=user,
                fullName=user.get_full_name() or user.username,
                phone=''
            )

        data = serializer.validated_data

        if 'fullName' in data:
            profile.fullName = data['fullName']

        if 'email' in data:
            request.user.email = data['email']
            request.user.save()

        if 'phone' in data:
            profile.phone = data['phone']

        if 'avatar' in data:
            avatar_data = data['avatar']
            if 'src' in avatar_data:
                profile.avatar = avatar_data['src']

        profile.save()

        return Response({
            "fullName": profile.fullName,
            "email": request.user.email,
            "phone": profile.phone,
            "avatar": {
                "src": profile.avatar.src.url if profile.avatar and profile.avatar.src else None,
                "alt": profile.avatar.alt if profile.avatar else "Аватар пользователя"
            }
        }, status=status.HTTP_200_OK)


class ChangePasswordView(APIView):
    """
    API endpoint для изменения пароля пользователя.

    Пример запроса:
    POST /profile/password/ - Изменение пароля пользователя

    Требует аутентификации.

    Request Body:
    {
        "currentPassword": "oldPass123",
        "newPassword": "newPass321"
    }

    Статусы ответов:
        200 - Пароль успешно изменен
        400 - Ошибки валидации данных
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
        Обработка POST-запроса для смены пароля.

        Args:
            request: Объект запроса с данными о текущем и новом пароле
        """
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer.save()

        return Response({
            "success": True,
            "message": "Пароль успешно изменен"
        }, status=status.HTTP_200_OK)


class AvatarUpdateView(APIView):
    """
    API endpoint для обновления аватара пользователя.

    Пример запроса:
    POST /profile/avatar/ - Изменение аватара пользователя

    Требует аутентификации.

    Статус ответа:
        200 - Аватар успешно обновлен
        400 - Файл не был передан в запросе
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
        Обработка POST-запроса для смены аватара.

        Args:
            request: Объект запроса с файлом аватара в request.FILES
        """
        user = request.user

        if 'avatar' not in request.FILES:
            return Response({
            'error': 'File is required',
            'message': 'Файл не был передан в запросе'
        }, status=status.HTTP_400_BAD_REQUEST)

        serializer = AvatarUpdateSerializer(
            instance=user,
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Аватар успешно обновлен"},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )


class TagListView(APIView):
    """
    API endpoint для списка тегов

    Пример запроса:
        GET /tags/ - список всех тегов

    Параметры:
    - category: фильтр по категории (опционально)

    Статус ответа:
        200 - Успешное получение данных
    """
    def get(self, request):
        """
        Получение списка тегов с возможностью фильтрации по категории.

        Args:
            request: Объект запроса с параметрами фильтрации
        """
        category_id = request.GET.get('category')
        tags = Tag.objects.all()

        if category_id:
            tags = tags.filter(product__category_id=category_id).distinct()

        serializer = TagSerializer(tags, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProductDetailView(APIView):
    """
    API endpoint для получения детальной информации о товаре.

    Пример запроса:
        - /product/1/ - Для получения деталей о первом товаре

    Статус ответа:
        200 - Товар найден и возвращен
        404 - Товар не найден
    """
    def get(self, request, id):
        """
        Получение детальной информации о товаре.

        Args:
            request: Объект запроса
            id: Идентификатор товара
        """
        product = get_object_or_404(
            Product.objects.select_related(
                'category'
            ).prefetch_related(
                'images',
                'tags',
                'product_reviews',
                'specifications'
            ),
            id=id
        )

        serializer = ProductDetailSerializer(product)

        return Response(serializer.data, status=status.HTTP_200_OK)


class CreateReviewView(APIView):
    """
    API endpoint для создания комментария к товару.

    Пример запроса:
        POST /product/{id}/review - добавить отзыв к товару

    Статус ответа:
        201 - Отзыв успешно создан
        400 - Ошибки валидации данных
        404 - Товар не найден
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id):
        """
        Создание отзыва для товара

        Args:
            request: Объект запроса с данными отзыва
            id: Идентификатор товара
        """
        get_object_or_404(Product, id=id)

        serializer = CreateReviewSerializer(
            data=request.data,
            context={
                'request': request,
                'product_id': id
            }
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        review = serializer.save()

        return Response(
            {
                'id': review.id,
                'message': 'Отзыв успешно добавлен'
            },
            status=status.HTTP_201_CREATED
        )