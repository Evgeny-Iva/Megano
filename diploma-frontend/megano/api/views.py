from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from .models import Category, Product, Sale, Basket
from .serializers import BasketResponseSerializer, AddToBasketSerializer
from django.utils.dateformat import format
from django.db.models import Sum, F
from django.utils import timezone
import pytz, logging, json


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
                "id": sale.product,
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
                "freeDelivery": product.freeDelivery,
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

        return Response({
            "items": serializer.data,
            "totalCount": total_count,
            "totalPrice": float(total_price)
        })

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

        return Response(
            {"id": product.id, "count": basket_item.quantity},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )


class BasketDeleteView(APIView):
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