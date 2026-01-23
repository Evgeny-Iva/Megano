from django.db import transaction
from django.core.exceptions import ValidationError

from ..models import Order, OrderItem, Basket, Product


class OrderService:
    """
    Сервис для работы с заказами

    Содержит бизнес-логику создания и обработки заказов.
    Отвечает за:
        - Создание заказа из корзины пользователя
        - Расчет стоимости доставки
        - Обработку транзакций
        - Валидацию бизнес-правил

    Методы:
        - create_simple_order(): Создание заказа из корзины
        и рассчитывает стоимость

    Исключения:
        - ValidationError: При нарушении бизнес-правил
    """

    @staticmethod
    @transaction.atomic
    def create_simple_order(user, data):
        """
        Создание простого заказа из корзины

        Args:
            user: Пользователь (User instance)
            data: Валидированные данные для Order

        Returns:
            Order: Созданный заказ

        Raises:
            ValidationError: Если корзина пуста или данные невалидны

        Бизнес-логика:
            1. Проверяет что корзина не пуста
            2. Создает заказ в транзакции
            3. Переносит товары из корзины в заказ
            4. Рассчитывает стоимость доставки
            5. Очищает корзину пользователя
            6. Возвращает созданный заказ
        """

        if not Basket.objects.filter(user=user).exists():
            raise ValidationError("Корзина пуста")

        order = Order.objects.create(user=user, **data)

        basket_items = Basket.objects.filter(user=user)
        items_total = 0
        for item in basket_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )
            items_total += item.product.price * item.quantity

        delivery_price = 0
        if data.get('deliveryType') == 'ordinary':
            delivery_price = 200 if items_total < 2000 else 0
        elif data.get('deliveryType') == 'express':
            delivery_price = 500

        order.totalCost = items_total + delivery_price
        order.deliveryPrice = delivery_price
        order.status = 'accepted'
        order.save()

        basket_items.delete()
        return order