import logging

from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from rest_framework import status


logger = logging.getLogger(__name__)

class AuthService:
    @staticmethod
    def authenticate_user(request, username, password):
        """Аутентификация. Возвращает user или None."""
        return authenticate(request, username=username, password=password)

    @staticmethod
    def login_user(request, user):
        """Логин. Ничего не возвращает."""
        login(request, user)

    @staticmethod
    def build_user_response(user):
        """Формирование словаря. Возвращает dict."""
        return {
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'fullName': user.get_full_name() or user.username,
            }
        }

    @staticmethod
    def register_user(username, password, name):
        """Регистрирует нового пользователя."""
        if User.objects.filter(username=username).exists():
            raise ValidationError("Username already exists")

        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=name
        )

        logger.info(f"User created: {user.id}")
        return user