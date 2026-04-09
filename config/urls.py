# c:/Users/skais/Desktop/Labo dev/DJANGO/django_polls/config/urls.py
"""
URL configuration for django_polls project.
"""
from django.contrib import admin
from django.urls import path, include

from polls.views import register

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('polls.urls')),
    path('accounts/register/', register, name='register'),
    path('accounts/', include('django.contrib.auth.urls')),
]
