from rest_framework import serializers
from django.utils.dateformat import format
import pytz
from .models import Basket, Product

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
            serializers.ValidationError: При любой ошибке валидации
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