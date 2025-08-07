from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('scenario/<int:scenario_id>/', views.phishing_scenario, name='phishing_scenario'),
]
