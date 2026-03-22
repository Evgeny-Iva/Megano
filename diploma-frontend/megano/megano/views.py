import os
from django.http import HttpResponse, Http404
from django.conf import settings


def serve_png(request, filename):
    """Обслуживает PNG файлы из папки frontend/static/frontend/"""
    file_path = os.path.join(settings.BASE_DIR, 'frontend', 'static', 'frontend', filename)

    if not os.path.exists(file_path):
        raise Http404("File not found")

    with open(file_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type='image/png')
        return response