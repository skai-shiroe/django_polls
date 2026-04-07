# c:/Users/skais/Desktop/Labo dev/DJANGO/django_polls/config/urls.py
"""
URL configuration for django_polls project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('polls.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
]
