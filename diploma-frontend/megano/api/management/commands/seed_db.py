from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from api.models import (
    Category, Product, Tag, ProductImage,
    Specification, Review, Profile, Avatar
)
from decimal import Decimal
from datetime import datetime, timedelta
import random


class Command(BaseCommand):
    help = 'Заполняет базу данных тестовыми данными'

    def handle(self, *args, **options):
        self.stdout.write('Начинаю заполнение базы данных...')

        # 1. Создаем тестового пользователя
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'first_name': 'Тест',
                'last_name': 'Пользователь'
            }
        )
        if created:
            user.set_password('testpass123')
            user.save()
            self.stdout.write(self.style.SUCCESS(f'✓ Создан пользователь: {user.username}'))

        # 2. Создаем аватар
        avatar = Avatar.objects.create(
            src='avatars/default.png',
            alt='Аватар по умолчанию'
        )

        # 3. Создаем профиль
        Profile.objects.get_or_create(
            user=user,
            defaults={
                'fullName': 'Тестовый Пользователь',
                'phone': 79991234567,
                'avatar': avatar
            }
        )
        self.stdout.write(self.style.SUCCESS('✓ Создан профиль пользователя'))

        # 4. Создаем категории
        categories_data = [
            {'title': 'Смартфоны', 'src': '/static/images/categories/smartphones.png', 'alt': 'Смартфоны'},
            {'title': 'Ноутбуки', 'src': '/static/images/categories/laptops.png', 'alt': 'Ноутбуки'},
            {'title': 'Компьютеры', 'src': '/static/images/categories/computers.png', 'alt': 'Компьютеры'},
            {'title': 'Электроника', 'src': '/static/images/categories/electronics.png', 'alt': 'Электроника'},
            {'title': 'Одежда', 'src': '/static/images/categories/clothes.png', 'alt': 'Одежда'},
            {'title': 'Обувь', 'src': '/static/images/categories/shoes.png', 'alt': 'Обувь'},
        ]

        categories = {}
        for cat_data in categories_data:
            cat, created = Category.objects.get_or_create(
                title=cat_data['title'],
                defaults={'src': cat_data['src'], 'alt': cat_data['alt']}
            )
            categories[cat.title] = cat
            self.stdout.write(f'  ✓ Категория: {cat.title}')

        # 5. Создаем теги
        tags_data = ['Новинка', 'Хит продаж', 'Распродажа', 'Популярное', 'Рекомендуем']
        tags = []
        for tag_name in tags_data:
            tag, created = Tag.objects.get_or_create(name=tag_name)
            tags.append(tag)
            self.stdout.write(f'  ✓ Тег: {tag.name}')

        # 6. Создаем товары
        products_data = [
            {
                'title': 'iPhone 15 Pro',
                'price': Decimal('99900.00'),
                'category': 'Смартфоны',
                'free_delivery': True,
                'count': 50,
                'description': 'Флагманский смартфон Apple с чипом A17 Pro',
                'tags': ['Новинка', 'Хит продаж'],
                'specifications': [
                    {'name': 'Экран', 'value': '6.1" Super Retina XDR'},
                    {'name': 'Процессор', 'value': 'A17 Pro'},
                    {'name': 'Память', 'value': '256 ГБ'},
                    {'name': 'Камера', 'value': '48 МП + 12 МП + 12 МП'},
                ]
            },
            {
                'title': 'MacBook Pro 14"',
                'price': Decimal('159900.00'),
                'category': 'Ноутбуки',
                'free_delivery': False,
                'count': 30,
                'description': 'Мощный ноутбук для профессионалов',
                'tags': ['Хит продаж', 'Популярное'],
                'specifications': [
                    {'name': 'Экран', 'value': '14.2" Liquid Retina XDR'},
                    {'name': 'Процессор', 'value': 'M3 Pro'},
                    {'name': 'Память', 'value': '16 ГБ'},
                    {'name': 'SSD', 'value': '512 ГБ'},
                ]
            },
            {
                'title': 'Nike Air Max',
                'price': Decimal('12990.00'),
                'category': 'Обувь',
                'free_delivery': True,
                'count': 100,
                'description': 'Кроссовки с воздушной подушкой',
                'tags': ['Популярное', 'Распродажа'],
                'specifications': [
                    {'name': 'Размер', 'value': '39-45'},
                    {'name': 'Материал', 'value': 'Текстиль/кожа'},
                    {'name': 'Сезон', 'value': 'Всесезонные'},
                ]
            },
            {
                'title': 'PlayStation 5',
                'price': Decimal('59990.00'),
                'category': 'Электроника',
                'free_delivery': False,
                'count': 25,
                'description': 'Игровая консоль нового поколения',
                'tags': ['Новинка', 'Хит продаж'],
                'specifications': [
                    {'name': 'Процессор', 'value': 'AMD Zen 2'},
                    {'name': 'Видеокарта', 'value': 'RDNA 2'},
                    {'name': 'Память', 'value': '16 ГБ'},
                    {'name': 'SSD', 'value': '825 ГБ'},
                ]
            },
            {
                'title': 'Футболка хлопковая',
                'price': Decimal('1990.00'),
                'category': 'Одежда',
                'free_delivery': True,
                'count': 200,
                'description': 'Мягкая футболка из 100% хлопка',
                'tags': ['Распродажа'],
                'specifications': [
                    {'name': 'Размер', 'value': 'S-XXL'},
                    {'name': 'Состав', 'value': '100% хлопок'},
                    {'name': 'Цвет', 'value': 'Белый, черный, синий'},
                ]
            },
            {
                'title': 'Gaming PC',
                'price': Decimal('89990.00'),
                'category': 'Компьютеры',
                'free_delivery': False,
                'count': 15,
                'description': 'Мощный игровой компьютер',
                'tags': ['Популярное'],
                'specifications': [
                    {'name': 'Процессор', 'value': 'Intel i7-13700K'},
                    {'name': 'Видеокарта', 'value': 'RTX 4070'},
                    {'name': 'Память', 'value': '32 ГБ'},
                    {'name': 'SSD', 'value': '1 ТБ'},
                ]
            },
        ]

        for prod_data in products_data:
            category = categories[prod_data['category']]
            product, created = Product.objects.get_or_create(
                title=prod_data['title'],
                defaults={
                    'price': prod_data['price'],
                    'category': category,
                    'free_delivery': prod_data['free_delivery'],
                    'count': prod_data['count'],
                    'description': prod_data['description'],
                    'rating': Decimal(str(random.uniform(4.0, 5.0))),
                    'reviews': random.randint(5, 50),
                }
            )

            # Добавляем теги
            for tag_name in prod_data['tags']:
                tag = Tag.objects.get(name=tag_name)
                product.tags.add(tag)

            # Создаем изображение
            ProductImage.objects.get_or_create(
                product=product,
                defaults={
                    'src': category.src,
                    'alt': product.title,
                    'is_main': True
                }
            )

            # Создаем спецификации
            for spec_data in prod_data['specifications']:
                Specification.objects.get_or_create(
                    product=product,
                    name=spec_data['name'],
                    defaults={'value': spec_data['value']}
                )

            # Создаем отзывы
            if created:
                for i in range(random.randint(1, 3)):
                    Review.objects.create(
                        product=product,
                        author=f'Покупатель {i + 1}',
                        email=f'buyer{i + 1}@example.com',
                        text=f'Отличный товар! Рекомендую. {product.title}',
                        rate=Decimal(str(random.uniform(4.0, 5.0)))
                    )

            self.stdout.write(f'  ✓ Товар: {product.title}')

        self.stdout.write(self.style.SUCCESS('\n✅ База данных успешно заполнена!'))
        self.stdout.write(f'\n📝 Тестовые данные:')
        self.stdout.write(f'   - Пользователь: testuser / testpass123')
        self.stdout.write(f'   - Количество товаров: {Product.objects.count()}')
        self.stdout.write(f'   - Количество категорий: {Category.objects.count()}')
        self.stdout.write(f'   - Количество отзывов: {Review.objects.count()}')