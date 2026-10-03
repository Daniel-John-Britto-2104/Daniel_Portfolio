from django.urls import path
from . import views

urlpatterns = [
    path("voice/", views.voice_webhook, name="voice_webhook"),
]