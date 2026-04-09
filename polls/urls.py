# c:/Users/skais/Desktop/Labo dev/DJANGO/django_polls/polls/urls.py
from django.urls import path
from . import views

app_name = 'polls'
urlpatterns = [
    path('', views.poll_list, name='list'),
    path('create/', views.poll_create, name='create'),
    path('<int:poll_id>/', views.vote, name='detail'),
    path('<int:poll_id>/results/', views.results, name='results'),
]
