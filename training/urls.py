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
    path('signup/', views.signup, name='signup'),
    path('accounts/profile/', views.profile, name='profile'),
    path("report/", views.report_view, name="report"),
    path("log_action/", views.log_action, name="log_action"),

    path("track/<uuid:run_uuid>/<int:step_id>/<slug:link_slug>/", views.track_link, name="track_link"),

    path("run/<uuid:run_uuid>/details/", views.view_risk_details, name="view_risk_details"),

    path("report/export.csv", views.reports_csv, name="reports_csv"),
    path(
        "track/<uuid:run_uuid>/<int:step_id>/<slug:link_slug>/",
        views.track_link,
        name="track_link",
    ),
    path(
        "run/<uuid:run_uuid>/step/<int:step_id>/link-preview/<slug:link_slug>/",
        views.link_preview,
        name="link_preview",
    ),
]
