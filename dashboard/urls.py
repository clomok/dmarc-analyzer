from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('domain/<int:domain_id>/', views.domain_detail, name='domain_detail'), # New Route
]