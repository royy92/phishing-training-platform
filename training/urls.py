from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('scenario/<int:scenario_id>/', views.phishing_scenario, name='phishing_scenario'),
    path('scenario/', views.scenario_list, name='scenario_list'),
    path('report/', views.report, name='report'),
    path('signup/', views.signup, name='signup'),
]
