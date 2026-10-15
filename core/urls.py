from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("request/", views.request_help, name="request_help"),
    path("request/submitted/<str:reference>/", views.request_submitted, name="request_submitted"),
    path("status/", views.track_request, name="track_request"),
]
