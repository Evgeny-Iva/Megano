from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator



class Avatar(models.Model):
    """Модель для хранения аватара пользователя"""

    src = models.ImageField(
        upload_to="app_users/avatars/user_avatars/",
        default="app_users/avatars/default.png",
        verbose_name="Ссылка",
    )
    alt = models.CharField(max_length=128, verbose_name="Описание")

    class Meta:
        verbose_name = "Аватар"
        verbose_name_plural = "Аватары"


class Profile(models.Model):
    """Модель профиля пользователя"""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile'
    )
    fullName = models.CharField(max_length=128, verbose_name="Полное имя")
    phone = models.PositiveIntegerField(
        blank=True, null=True, unique=True, verbose_name="Номер телефона"
    )
    balance = models.DecimalField(
        decimal_places=2, max_digits=10, default=0, verbose_name="Баланс"
    )
    avatar = models.ForeignKey(
        Avatar,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="Аватар",
    )


class Category(models.Model):
    title = models.CharField(max_length=200)
    src = models.CharField(max_length=500)
    alt = models.CharField(max_length=200)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subcategories'
    )

    def __str__(self):
        return self.title


class Product(models.Model):
    """Модель товаров"""

    title = models.CharField(max_length=100, verbose_name="Название товара")
    price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Цена"
    )
    category = models.ForeignKey(
        'Category',
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name="Категория"
    )
    freeDelivery = models.BooleanField(
        default=False, verbose_name="Бесплатная доставка"
    )
    rating = models.DecimalField(
        max_digits=3, decimal_places=1, default=0, verbose_name="Рейтинг"
    )
    tags = models.ManyToManyField('Tag', blank=True)
    date = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    count = models.IntegerField(default=0, verbose_name="Количество на складе")
    description = models.TextField(verbose_name="Описание товара")
    reviews = models.IntegerField(default=0, verbose_name="Количество отзывов")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"


class Tag(models.Model):
    """Модель тегов"""

    name = models.CharField(max_length=100, verbose_name="Название тега")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Тег"
        verbose_name_plural = "Теги"


class ProductImage(models.Model):
    """Модель для хранения фотографий товаров"""

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images'
    )
    src = models.CharField(max_length=500, verbose_name="Путь к изображению")
    alt = models.CharField(
        max_length=200, blank=True, verbose_name="Альтернативный текст"
    )
    order = models.IntegerField(default=0)
    is_main = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Изображение товара"
        verbose_name_plural = "Изображения товаров"
        ordering = ['order', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['product'],
                condition=models.Q(is_main=True),
                name='unique_main_image_per_product'
            )
        ]

    def __str__(self):
        return f"Изображение для {self.product.title}"


class SaleManager(models.Manager):
    def get_active(self):
        today = timezone.now().date()
        return self.filter(date_from__lte=today, date_to__gte=today)

    def get_expired(self):
        today = timezone.now().date()
        return self.filter(date_to__gte=today)


class Sale(models.Model):
    """Модель скидок на товары"""

    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        related_name='sales',
        verbose_name="Товар"
    )
    sale_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Цена со скидкой"
    )
    date_from = models.DateField(verbose_name="Дата начала скидки")
    date_to = models.DateField(verbose_name="Дата окончания скидки")

    class Meta:
        verbose_name = "Скидка"
        verbose_name_plural = "Скидки"
        ordering = ['-date_from']

    objects = SaleManager()

    def __str__(self):
        return f"Скидка на {self.product.title}"

    @property
    def is_active(self):
        """Проверяет, активна ли скидка сейчас"""
        today = timezone.now().date()
        return self.date_from <= today <= self.date_to

    @property
    def discount_percentage(self):
        """Вычисляет процент скидки"""
        if self.product.price > 0:
            discount = ((self.product.price - self.sale_price) / self.product.price) * 100
            return round(discount, 1)
        return 0


class Basket(models.Model):
    """Модель для хранения товаров в корзине пользователя"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Пользователь",
    )

    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        verbose_name="Товар",
    )

    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name="Количество",
    )

    class Meta:
        verbose_name = "Корзина"
        verbose_name_plural = "Корзины"
        unique_together = ['user', 'product']

    def __str__(self):
        return f"{self.user.username} - {self.product.title} x{self.quantity}"

    @property
    def total_price(self):
        """Общая стоимость позиции"""
        return self.product.price * self.quantity


class Order(models.Model):
    """Модель заказа пользователя."""
    STATUS_CHOICES = [
        ('pending', 'В обработке'),
        ('accepted', 'Принят'),
        ('paid', 'Оплачен'),
        ('shipped', 'Отправлен'),
        ('delivered', 'Доставлен'),
        ('cancelled', 'Отменён'),
    ]

    DELIVERY_CHOICES = [
        ('free', 'Бесплатная'),
        ('express', 'Экспресс'),
        ('pickup', 'Самовывоз'),
    ]

    PAYMENT_CHOICES = [
        ('online', 'Онлайн'),
        ('card', 'Картой при получении'),
        ('cash', 'Наличными при получении'),
    ]

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    full_name = models.CharField(max_length=100, verbose_name="Полное имя")
    email = models.EmailField(verbose_name="Email")
    phone = models.CharField(max_length=20, verbose_name="Телефон")
    city = models.CharField(max_length=100, verbose_name="Город")
    address = models.CharField(max_length=200, verbose_name="Адрес")

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name="Пользователь"
    )

    delivery_type = models.CharField(
        max_length=20,
        choices=DELIVERY_CHOICES,
        default='free',
        verbose_name="Тип доставки"
    )

    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_CHOICES,
        default='online',
        verbose_name="Тип оплаты"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Статус"
    )

    total_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Общая стоимость"
    )

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ['-created_at']

    def __str__(self):
        return f"Заказ #{self.id} - {self.fullName} ({self.status})"

    def save(self, *args, **kwargs):
        """Автоматически считаем сумму при сохранении"""
        if not self.total_cost and hasattr(self, 'items'):
            self.total_cost = sum(item.total_price for item in self.items.all())
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    """Товар в заказе (связь Order-Product с количеством и фиксированной ценой)."""
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Заказ"
    )

    product = models.ForeignKey(
        'Product',
        on_delete=models.PROTECT,
        related_name='order_items',
        verbose_name="Товар"
    )

    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Количество"
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Цена на момент заказа"
    )

    class Meta:
        verbose_name = "Товар в заказе"
        verbose_name_plural = "Товары в заказе"
        unique_together = ['order', 'product']

    def __str__(self):
        return f"{self.product.title} x{self.quantity} (заказ #{self.order.id})"

    @property
    def total_price(self):
        return self.price * self.quantity

    def save(self, *args, **kwargs):
        """При сохранении фиксируем текущую цену товара"""
        if not self.price:
            self.price = self.product.price
        super().save(*args, **kwargs)


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_reviews')
    author = models.CharField(max_length=100, verbose_name="Автор")
    email = models.EmailField(verbose_name="Email")
    text = models.TextField(max_length=300, verbose_name="Комментарий")
    date = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    rate = models.DecimalField(
        max_digits=3, decimal_places=1, default=0, verbose_name="Рейтинг"
    )

    class Meta:
        verbose_name = "Комментарии в товаре"
        verbose_name_plural = "Комментарии в товарах"


class Specification(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='specifications')
    name = models.CharField(max_length=100, verbose_name="Характеристика")
    value = models.CharField(max_length=300, verbose_name="Значение")

    class Meta:
        verbose_name = "Спецификация товара"
        verbose_name_plural = "Спецификация товаров"