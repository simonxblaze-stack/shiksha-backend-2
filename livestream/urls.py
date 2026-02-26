from django.urls import path
from .views import (
    join_live_session,
    create_live_session,
    livekit_webhook,
    StudentLiveSessionListView,
    TeacherLiveSessionListView,
)

urlpatterns = [
    path("student/sessions/", StudentLiveSessionListView.as_view()),
    path("teacher/sessions/", TeacherLiveSessionListView.as_view()),
    path("sessions/", create_live_session),
    path("sessions/<uuid:session_id>/join/", join_live_session),
    path("webhook/", livekit_webhook),
]
