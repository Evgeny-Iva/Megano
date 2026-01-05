from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from .models import Category, Product
from django.utils.dateformat import format
import json
import pytz


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


class CategoryListView(APIView):
    def get(self, request):
        name = Category.object.all

        categories_data = []
        for category in name:
            category_dict = {
                'id': category.id,
                'title': category.title,
                'image': {
                    'src': category.image_src,
                    'alt': category.image_alt,
                },
                'subcategories': []
            }
            categories_data.append(category_dict)

        return Response(categories_data)


class CatalogView(APIView):
    def get(self, request):
        products = Product.objects.all()

        category_id = request.GET.get('category')
        search = request.GET.get('filter', '').strip()
        sort_type = request.GET.get('sortType', 'dec')
        limit = int(request.GET.get('limit', 20))
        current_page = int(request.GET.get('currentPage', 1))

        if category_id:
            products = products.filter(category_id=category_id)

        if search:
            products = products.filter(title__icontains=search)

        if sort_type == 'inc':
            products = products.order_by('price')
        else:
            products = products.order_by('-price')

        total_count = products.count()
        last_page = (total_count + limit - 1) // limit

        offset = (current_page - 1) * limit
        products = products[offset:offset + limit]

        products = products.select_related('category')\
            .prefetch_related('tags', 'images')

        items = []
        for product in products:
            date_str = format(
                product.date.astimezone(pytz.timezone('Europe/Moscow')),
                'D M d Y H:i:s O'
            )
            item = {
                "id": product.id,
                "title": product.title,
                "price": float(product.price),
                "category": product.category.id,
                "freeDelivery": product.freeDelivery,
                "rating": float(product.rating),
                "date": date_str,
                "count": product.count,
                "description": product.description,
                "reviews": product.reviews,
            }

            item.update({
                "tags": [{"id": t.id, "name": t.name} for t in product.tags.all()],
                "images": [{"src": i.src, "alt": i.alt} for i in product.images.all()]
            })

            items.append(item)

        return Response({
            "items": items,
            "currentPage": current_page,
            "lastPage": last_page
        })


