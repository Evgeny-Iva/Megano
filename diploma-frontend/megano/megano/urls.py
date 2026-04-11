"""
URL configuration for megano project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve
from django.views.generic import RedirectView
from . import views
import os

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", include("frontend.urls")),
    path('api/', include('api.urls')),


]


if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += [
        path('smartphones.png', serve, {'document_root': os.path.join(settings.BASE_DIR, 'static', 'images', 'categories'), 'path': 'smartphones.png'}),
        path('shoes.png', serve, {'document_root': os.path.join(settings.BASE_DIR, 'static', 'images', 'categories'), 'path': 'shoes.png'}),
        path('clothes.png', serve, {'document_root': os.path.join(settings.BASE_DIR, 'static', 'images', 'categories'), 'path': 'clothes.png'}),
        path('laptops.png', serve, {'document_root': os.path.join(settings.BASE_DIR, 'static', 'images', 'categories'), 'path': 'laptops.png'}),
        path('computers.png', serve, {'document_root': os.path.join(settings.BASE_DIR, 'static', 'images', 'categories'), 'path': 'computers.png'}),
        path('electronics.png', serve, {'document_root': os.path.join(settings.BASE_DIR, 'static', 'images', 'categories'), 'path': 'electronics.png'}),
    ]
