from django.urls import path
from . import views

app_name = "training"

urlpatterns = [
    path('', views.home, name='home'),
    path('scenario/<int:pk>/', views.scenario_view, name='scenario'),
    path("scenario/<int:scenario_id>/", views.phishing_scenario, name="phishing_scenario"),
    path("scenario/retake/<int:scenario_id>/", views.retake_scenario, name="retake_scenario"),
    path("track/landing/<int:scenario_id>/", views.track_landing, name="track_landing"),
    path('scenario/', views.scenario_list, name='scenario_list'),
    path("reports/", views.report, name="report"),
    path('signup/', views.signup, name='signup'),
    path("category/<slug:slug>/", views.category_detail, name="category_detail"),
]
