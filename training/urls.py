from django.urls import path
from . import views

app_name = "training"

urlpatterns = [
    path('', views.home, name='home'),

    path("category/<slug:slug>/", views.category_detail, name="category_detail"),
    path("scenario/<int:scenario_id>/", views.run_start, name="phishing_scenario"),
    path('scenario/<int:scenario_id>/start/', views.run_start, name='run_start'),

    path('run/<uuid:run_uuid>/step/<int:index>/', views.run_step, name='run_step'),
    path('run/<uuid:run_uuid>/action/', views.run_action, name='run_action'),
    path('run/<uuid:run_uuid>/summary/', views.run_summary, name='run_summary'),

    path('track/<uuid:run_uuid>/<int:step_id>/<slug:link_slug>/', views.track_link, name='track_link'),

    path("report/", views.report, name="report"),
    path("report/export.csv", views.reports_csv, name="reports_csv"),
]
