from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),

    # Public side
    path("request/", views.request_help, name="request_help"),
    path("request/submitted/<str:reference>/", views.request_submitted, name="request_submitted"),
    path("status/", views.track_request, name="track_request"),
    path("offer/", views.offer_resources, name="offer_resources"),
    path("offer/thanks/", views.offer_thanks, name="offer_thanks"),
    path("shelters/", views.find_help, name="find_help"),

    # Organization side
    path("login/", auth_views.LoginView.as_view(template_name="core/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/request/<int:pk>/update/", views.update_request, name="update_request"),
    path("dashboard/offers/", views.dashboard_offers, name="dashboard_offers"),
    path("dashboard/offers/<int:pk>/update/", views.update_offer, name="update_offer"),
]
