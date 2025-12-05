from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('domain/<int:domain_id>/', views.domain_detail, name='domain_detail'),
    
    # --- NEW: This is the missing line causing the error ---
    path('threats/', views.active_threats, name='active_threats'),
    
    path('ingest/trigger/', views.trigger_ingest, name='trigger_ingest'),
    path('report/<int:report_id>/ack/', views.acknowledge_report, name='acknowledge_report'),
]