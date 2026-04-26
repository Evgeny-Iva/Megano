# Django Backend для интернет-магазина

Бэкенд интернет-магазина с полным функционалом: каталог, корзина, заказы, оплата, авторизация и профиль пользователя.


> **📌 Важно:** Этот репозиторий содержит **бэкенд-часть** проекта.  
> Фронтенд (Java) находится в отдельной папке `/frontend` и используется только для тестирования API.  
> Вся логика бэкенда написана мной.

## 🚀 Технологии

- Python 3.11
- Django 4.2
- Django REST Framework
- SQLite
- Git

## 📦 Возможности

- Каталог товаров (фильтрация, сортировка, пагинация)
- Корзина (добавление, удаление, изменение количества)
- Заказы (оформление, история)
- Оплата (валидация карты)
- Авторизация (сессии + JWT)
- Профиль пользователя (смена пароля, аватар)
- Команда для заполнения БД тестовыми данными

## API Примеры

### Каталог товаров
```http
GET /api/catalog/?category=1&sortType=inc&limit=20

Ответ:
{
  "items": [
    {
      "id": 6,
      "title": "Футболка хлопковая",
      "price": 1990.00,
      "category": 5,
      "freeDelivery": true,
      "rating": 4.7,
      "images": [{"src": "/clothes.png", "alt": "Футболка хлопковая"}]
    }
  ],
  "currentPage": 1,
  "lastPage": 3
}
```


### Добавление в корзину
```
POST /api/basket/
Content-Type: application/json

{
  "id": 6,
  "count": 2
}

Ответ:
{
  "id": 6,
  "count": 2
}
```

### Оформление заказа
```
POST /api/orders/
Content-Type: application/json

{
  "deliveryType": "free",
  "paymentType": "online",
  "city": "Москва",
  "address": "ул. Ленина, 10"
}

Ответ:
{
  "orderId": 5,
  "totalCost": "3980.00",
  "status": "pending"
}
```

### Оплата заказа
```
POST /api/payment/5/
Content-Type: application/json

{
  "number": "1234567890123456",
  "name": "Ivan Ivanov",
  "month": "12",
  "year": "2025",
  "code": "123"
}

Ответ:
{
  "success": true,
  "orderId": 5,
  "status": "paid"
}
```

### Авторизация
```
POST /api/sign-in/
Content-Type: application/json

{
  "username": "testuser",
  "password": "testpass123"
}

Ответ:
{
  "user": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "fullName": "Тестовый Пользователь"
  }
}
```

## 🛠️ Установка и запуск

### 1. Клонировать репозиторий
```bash
git clone [ссылка на репозиторий]
cd diploma-frontend/megano
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # Mac/Linux
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_db
python manage.py runserver
```

## Ссылка на проект
[https://github.com/Evgeny-Iva/Megano](https://github.com/Evgeny-Iva/Megano)

## Автор
Евгений Иванов — [GitHub](https://github.com/Evgeny-Iva)