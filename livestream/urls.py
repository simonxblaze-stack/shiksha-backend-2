from django.urls import path
from .views import livekit_webhook

urlpatterns = [
    path("webhook/", livekit_webhook),
    path("webhook", livekit_webhook),
]
