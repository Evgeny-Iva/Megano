from rest_framework import serializers
from django.utils.dateformat import format
import pytz
from .models import Basket, Product, Order, OrderItem
from datetime import datetime


class BasketResponseSerializer(serializers.Serializer):
    """
    Сериализатор для преобразования Basket объектов в формат корзины.

    Преобразует Basket запись в JSON с полной информацией о товаре
    и количеством в корзине. Все поля только для чтения.

    Пример выходных данных:
        {
            "id": 123,
            "category": 55,
            "price": 500.67,
            "count": 3,
            "date": "Thu Feb 09 2023 21:39:52 GMT+0100",
            "title": "video card",
            "description": "description of the product",
            "freeDelivery": true,
            "images": [{"src": "/3.png", "alt": "Image alt string"}],
            "tags": [{"id": 12, "name": "Gaming"}],
            "reviews": 5,
            "rating": 4.6
        }

    Примечания:
        - Все поля только для чтения (read-only)
        - Поле 'count' берётся из Basket.quantity, а не из Product.count
        - Изображения: всегда возвращается массив (пустой или с одним изображением)
    """

    id = serializers.IntegerField(source='product.id')
    category = serializers.IntegerField(source='product.category.id')
    price = serializers.DecimalField(source='product.price', max_digits=10, decimal_places=2)
    count = serializers.IntegerField(source='quantity')
    date = serializers.SerializerMethodField()
    title = serializers.CharField(source='product.title')
    description = serializers.CharField(source='product.description')
    freeDelivery = serializers.BooleanField(source='product.freeDelivery')
    reviews = serializers.IntegerField(source='product.reviews')
    rating = serializers.FloatField(source='product.rating')
    images = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()

    def get_date(self, obj):
        date_obj = obj.product.date
        return format(
            date_obj.astimezone(pytz.timezone('Europe/Moscow')),
            'D M d Y H:i:s O'
        )

    def get_images(self, obj):
        first_image = obj.product.images.first()
        if first_image:
            return [{"src": first_image.src, "alt": first_image.alt}]
        return []

    def get_tags(self, obj):
        return [
            {"id": tag.id, "name": tag.name}
            for tag in obj.product.tags.all()
        ]


class AddToBasketSerializer(serializers.Serializer):
    """
    Сериализатор для валидации данных при добавлении товара в корзину.

    Используется в BasketView.post() для обработки POST /api/basket/.
    """

    id = serializers.IntegerField()
    count = serializers.IntegerField(min_value=1, default=1)

    def validate(self, data):
        """
        Проводит комплексную валидацию данных.

        Проверки:
        1. Существует ли товар с указанным id
        2. Достаточно ли товара на складе

        Returns:
            dict: Валидированные данные с добавленным объектом product

        Raises:
            serializers. ValidationError: При любой ошибке валидации
        """

        product_id = data['id']
        count = data['count']

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            raise serializers.ValidationError({"id": "Product not found"})

        if count > product.count:
            raise serializers.ValidationError({
                "count": f"Available only {product.count} items"
            })

        data['product'] = product
        return data


class OrderItemSerializer(serializers.ModelSerializer):
    """Сериализатор для товара в заказе (вложенный)"""
    id = serializers.IntegerField(source='product.id')
    category = serializers.IntegerField(source='product.category.id')
    price = serializers.DecimalField(source='price', max_digits=10, decimal_places=2)
    count = serializers.IntegerField(source='quantity')
    date = serializers.SerializerMethodField()
    title = serializers.CharField(source='product.title')
    description = serializers.CharField(source='product.description')
    freeDelivery = serializers.BooleanField(source='product.free_delivery')
    images = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    reviews = serializers.IntegerField(source='product.reviews')
    rating = serializers.FloatField(source='product.rating')

    def get_date(self, obj):
        date_obj = obj.product.date
        return format(
            date_obj.astimezone(pytz.timezone('Europe/Moscow')),
            'D M d Y H:i:s O'
        )

    def get_images(self, obj):
        first_image = obj.product.images.first()
        if first_image:
            return [{"src": first_image.src, "alt": first_image.alt}]
        return []

    def get_tags(self, obj):
        return [
            {"id": tag.id, "name": tag.name}
            for tag in obj.product.tags.all()
        ]

    class Meta:
        model = OrderItem
        fields = [
            'id', 'category', 'price', 'count', 'date',
            'title', 'description', 'freeDelivery',
            'images', 'tags', 'reviews', 'rating'
        ]


class OrderSerializer(serializers.ModelSerializer):
    """Основной сериализатор заказа"""
    products = OrderItemSerializer(source='items', many=True, read_only=True)
    createdAt = serializers.DateTimeField(
        source='created_at',
        format='%Y-%m-%d %H:%M',
        read_only=True
    )

    class Meta:
        model = Order
        fields = [
            'id', 'createdAt', 'fullName', 'email', 'phone',
            'deliveryType', 'paymentType', 'totalCost', 'status',
            'city', 'address', 'products'
        ]
        read_only_fields = ['id', 'createdAt', 'totalCost', 'status']

    def validate(self, data):
        """Проверяем что корзина не пустая"""
        request = self.context.get('request')
        if request and not Basket.objects.filter(user=request.user).exists():
            raise serializers.ValidationError({"detail": "Корзина пуста"})
        return data


class CreateOrderSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания нового заказа

    Валидирует данные перед созданием заказа:
    - Проверяет обязательные поля
    - Валидирует форматы данных

    Fields:
    - fullName: Полное имя получателя (строка, обязательно)
    - email: Email получателя (email, обязательно)
    - phone: Телефон получателя (строка, обязательно)
    - deliveryType: Тип доставки ['ordinary', 'express'] (строка, обязательно)
    - paymentType: Тип оплаты ['online', 'cash'] (строка, обязательно)
    - city: Город доставки (строка, обязательно для express доставки)
    - address: Адрес доставки (строка, обязательно)

    Пример запроса:
    {
        "fullName": "Иван Иванов",
        "email": "ivan@example.com",
        "phone": "+79991234567",
        "deliveryType": "ordinary",
        "paymentType": "online",
        "city": "Москва",
        "address": "ул. Примерная, 1"
    }
    """

    class Meta:
        model = Order
        fields = [
            'fullName', 'email', 'phone',
            'deliveryType', 'paymentType',
            'city', 'address'
        ]


class PaymentSerializer(serializers.ModelSerializer):
    """
    Сериализатор для данных оплаты

    Валидирует данные банковской карты:
        - number: Номер карты (16-19 цифр)
        - name: Имя владельца (строка)
        - month: Месяц действия (01-12)
        - year: Год действия (2023-2030)
        - code: CVV код (3-4 цифры)
    """
    number = serializers.CharField(max_length=19)
    name = serializers.CharField(max_length=50)
    month = serializers.CharField(max_length=2)
    year = serializers.CharField(max_length=4)
    code = serializers.CharField(max_length=4)

    def validate_number(self, value):
        """Валидация номера карты"""
        cleaned = value.replace(" ", "").replace("-", "")

        if not cleaned.isdigit():
            raise serializers.ValidationError(
                "Номер карты должен содержать только цифры"
            )

        if len(cleaned) not in [16, 19]:
            raise serializers.ValidationError(
                "Номер карты должен содержать 16 или 19 цифр"
            )

        return cleaned

    def validate_month(self, value):
        """Валидация месяца"""
        if not value.isdigit():
            raise serializers.ValidationError(
                "Месяц должен содержать только цифры"
            )

        if len(value) != 2:
            raise serializers.ValidationError(
                "Месяц должен содержать 2 цифр"
            )

        month_num = int(value)
        if 0 < month_num < 13:
            raise serializers.ValidationError(
                "Месяц должен содержать цифр от 1 до 12 включительно"
            )

        return value.zfill(2)

    def validate_year(self, value):
        """Валидация года"""
        if not value.isdigit():
            raise serializers.ValidationError(
                "Год должен содержать только цифры"
            )

        if len(value) != 4:
            raise serializers.ValidationError(
                "Год должен содержать 4 цифр"
            )

        year_num = int(value)
        current_year = datetime.now().year
        if current_year > year_num:
            raise serializers.ValidationError(
                "Год карты устарел"
            )

        if year_num > current_year + 10:
            raise serializers.ValidationError(
                "Срок действия карты слишком большой"
            )

        return value

    def validate_code(self, value):
        """Валидация CVV кода"""
        if not value.isdigit():
            raise serializers.ValidationError(
                "CVV код должен содержать только цифры"
            )

        if len(value) not in [3, 4]:
            raise serializers.ValidationError(
                "CVV код должен содержать 3 или 4 цифр"
            )

        return value

    def validate(self, data):
        """Дополнительная валидация: срок действия карты"""
        month = int(data['month'])
        year = int(data['year'])
        current_year = datetime.now().year
        current_month = datetime.now().month

        if year == current_year and month < current_month:
            raise serializers.ValidationError({
                "expiry": "Срок действия карты истек"
            })

        return data