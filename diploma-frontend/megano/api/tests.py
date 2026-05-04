from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from .models import Product, Category



class CatalogTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.category = Category.objects.create(
            title='Test Category',
            src='/static/test.jpg',
            alt='Test'
        )
        self.product = Product.objects.create(
            title='Test Phone',
            price=9999,
            count=10,
            category=self.category
        )

    def test_catalog_page(self):
        """GET /api/catalog/ возвращает 200"""
        response = self.client.get('/api/catalog/')
        self.assertEqual(response.status_code, 200)

    def test_basket_unauthorized(self):
        """POST /api/basket/ без авторизации → 401 или 403"""
        self.client.logout()
        response = self.client.post('/api/basket/', {'id': self.product.id, 'count': 1})
        self.assertIn(response.status_code, [401, 403])

    def test_basket_authorized(self):
        """POST /api/basket/ авторизованным → 200"""
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/basket/', {'id': self.product.id, 'count': 1})
        self.assertEqual(response.status_code, 200)


class SignUpViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/sign-up/'

        self.existing_user = User.objects.create_user(
            username='existing_user',
            password='oldpassword123',
            first_name='Existing'
        )

    def test_successful_registration(self):
        """Тест: успешная регистрация нового пользователя"""
        data = {
            'username': 'testuser',
            'password': 'testpassword123',
            'name': 'Test User'
        }

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, 200)

        self.assertTrue(User.objects.filter(username='testuser').exists())

    def test_registration_missing_username(self):
        """Тест: ошибка при отсутствии username"""
        data = {
            'password': 'testpassword123',
            'name': 'Test User'
        }

        count_before = User.objects.count()

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, 400)

        count_after = User.objects.count()
        assert count_before == count_after

    def test_registration_existing_username(self):
        """Тест: ошибка при создании существующего username"""
        data = {
            'username': 'existing_user',
            'password': 'testpassword123',
            'name': 'Test User'
        }

        count_before = User.objects.count()

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, 400)

        count_after = User.objects.count()
        assert count_before == count_after
