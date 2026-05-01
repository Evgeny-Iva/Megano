from django.contrib.auth import authenticate, login
from rest_framework import status

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