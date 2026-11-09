from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("request/", views.request_help, name="request_help"),
    path("request/submitted/<str:reference>/", views.request_submitted, name="request_submitted"),
    path("status/", views.track_request, name="track_request"),

    # Organization side
    path("login/", auth_views.LoginView.as_view(template_name="core/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/request/<int:pk>/update/", views.update_request, name="update_request"),
]
