from django.urls import path
from . import views

urlpatterns = [
    path("voice/", views.voice_webhook, name="voice_webhook"),
    path("chat/", views.chat_endpoint, name="chat_endpoint"),
    path("tts/", views.tts_endpoint, name="tts_endpoint"),
]