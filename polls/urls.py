from django.urls import path
from . import views

app_name = 'polls'
urlpatterns = [
    path('', views.poll_list, name='list'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('create/', views.poll_create, name='create'),
    path('<int:poll_id>/', views.vote, name='detail'),
    path('<int:poll_id>/results/', views.results, name='results'),
    path('<int:poll_id>/export/csv/', views.export_poll_csv, name='export_csv'),
    path('<int:poll_id>/export/pdf/', views.export_poll_pdf, name='export_pdf'),
]
