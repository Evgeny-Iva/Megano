# api/management/commands/seed_db.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
import random
from datetime import timedelta


class Command(BaseCommand):
    help = 'Заполняет базу данных тестовыми данными'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Начинаю заполнение базы данных...'))

        try:
            # Пробуем импортировать модели
            from api.models import (
                Profile, Avatar, Category, Product, Tag, ProductImage,
                Specification, Review, Sale, Basket, Order, OrderItem
            )
            self.stdout.write(self.style.SUCCESS('Модели успешно импортированы'))

            # Запускаем заполнение
            self.seed_database(
                Profile, Avatar, Category, Product, Tag, ProductImage,
                Specification, Review, Sale, Basket, Order, OrderItem
            )

        except ImportError as e:
            self.stdout.write(self.style.ERROR(f'Ошибка импорта: {e}'))
            self.stdout.write('Проверьте структуру моделей в api/models/')

    def seed_database(self, Profile, Avatar, Category, Product, Tag,
                      ProductImage, Specification, Review, Sale,
                      Basket, Order, OrderItem):
        """Основная логика заполнения базы"""

        # 1. Создаем базовых пользователей
        self.stdout.write('Создаю пользователей...')

        # Создаем админа
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@shop.ru',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()

        # Создаем обычного пользователя
        user, created = User.objects.get_or_create(
            username='user1',
            defaults={
                'email': 'user1@shop.ru',
                'is_staff': False
            }
        )
        if created:
            user.set_password('user1123')
            user.save()

        self.stdout.write(self.style.SUCCESS('Пользователи созданы'))

        # 2. Создаем тестовый товар (минимальный набор)
        self.stdout.write('Создаю тестовый товар...')

        # Создаем категорию
        category, _ = Category.objects.get_or_create(
            title='Электроника',
            defaults={
                'src': '/electronics.png',
                'alt': 'Электроника'
            }
        )

        # Создаем товар
        product = Product.objects.create(
            title='Тестовый товар',
            price=Decimal('9999.99'),
            category=category,
            count=10,
            description='Описание тестового товара'
        )

        self.stdout.write(self.style.SUCCESS(f'Товар создан: {product.title}'))

        self.stdout.write(self.style.SUCCESS('База данных заполнена минимальными данными!'))