from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
import json


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
