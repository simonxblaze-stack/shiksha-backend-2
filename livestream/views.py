import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.db import transaction

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from livekit.api import WebhookReceiver

from enrollments.models import Enrollment
from .models import LiveSession, LiveSessionAttendance
from .services import generate_livekit_token
from .serializers import (
    LiveSessionCreateSerializer,
    LiveSessionListSerializer,
)

logger = logging.getLogger(__name__)


class StudentLiveSessionListView(generics.ListAPIView):
    serializer_class = LiveSessionListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if not user.has_role("student"):
            raise PermissionDenied("Only students allowed.")

        active_courses = Enrollment.objects.filter(
            user=user,
            status=Enrollment.STATUS_ACTIVE
        ).values_list("course_id", flat=True)

        return (
            LiveSession.objects
            .filter(course_id__in=active_courses)
            .select_related("course", "subject", "created_by")
            .order_by("start_time")
        )


class TeacherLiveSessionListView(generics.ListAPIView):
    serializer_class = LiveSessionListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if not user.has_role("teacher"):
            raise PermissionDenied("Only teachers allowed.")

        return (
            LiveSession.objects
            .filter(created_by=user)
            .select_related("course", "subject")
            .order_by("start_time")
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def join_live_session(request, session_id):
    user = request.user
    session = get_object_or_404(LiveSession, id=session_id)
    now = timezone.now()

    if session.status == LiveSession.STATUS_CANCELLED:
        return Response({"detail": "Session cancelled"}, status=400)

    if now > session.end_time:
        return Response({"detail": "Session ended"}, status=403)

    # STUDENT
    if user.has_role("student"):

        is_enrolled = Enrollment.objects.filter(
            user=user,
            course=session.course,
            status=Enrollment.STATUS_ACTIVE,
        ).exists()

        if not is_enrolled:
            return Response({"detail": "Not enrolled"}, status=403)

        if now < session.start_time - timedelta(minutes=10):
            return Response({"detail": "Too early to join"}, status=403)

        is_teacher = False

    # TEACHER
    elif user.has_role("teacher"):

        if not session.subject.teachers.filter(id=user.id).exists():
            return Response({"detail": "Not assigned to this subject"}, status=403)

        is_teacher = True

    else:
        return Response({"detail": "Unauthorized role"}, status=403)

    token = generate_livekit_token(
        user=user,
        session=session,
        is_teacher=is_teacher,
    )

    return Response({
        "livekit_url": settings.LIVEKIT_URL,
        "token": token,
        "room": session.room_name,
        "role": "teacher" if is_teacher else "student",
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_live_session(request):
    serializer = LiveSessionCreateSerializer(
        data=request.data,
        context={"request": request}
    )

    if serializer.is_valid():
        session = serializer.save()
        return Response(
            {
                "id": session.id,
                "room": session.room_name,
                "status": session.status,
            },
            status=status.HTTP_201_CREATED
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
def livekit_webhook(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    receiver = WebhookReceiver(
        settings.LIVEKIT_API_KEY,
        settings.LIVEKIT_API_SECRET,
    )

    try:
        event = receiver.receive(
            request.body,
            request.headers.get("Authorization"),
        )

        logger.info(f"LiveKit event: {event.event}")

        handlers = {
            "participant_joined": _handle_participant_join,
            "participant_left": _handle_participant_left,
            "room_started": _handle_room_started,
            "room_finished": _handle_room_finished,
        }

        handler = handlers.get(event.event)
        if handler:
            handler(event)

        return HttpResponse(status=200)

    except Exception:
        logger.exception("Webhook error")
        return HttpResponse(status=400)


@transaction.atomic
def _handle_participant_join(event):
    room_name = event.room.name
    identity = str(event.participant.identity)

    session = LiveSession.objects.filter(room_name=room_name).first()
    if not session:
        return

    LiveSessionAttendance.objects.update_or_create(
        session=session,
        user_id=identity,
        defaults={"joined_at": timezone.now()}
    )


@transaction.atomic
def _handle_participant_left(event):
    room_name = event.room.name
    identity = str(event.participant.identity)

    session = LiveSession.objects.filter(room_name=room_name).first()
    if not session:
        return

    attendance = LiveSessionAttendance.objects.filter(
        session=session,
        user_id=identity
    ).first()

    if attendance:
        attendance.left_at = timezone.now()
        attendance.save()


def _handle_room_started(event):
    LiveSession.objects.filter(
        room_name=event.room.name
    ).update(status=LiveSession.STATUS_LIVE)


def _handle_room_finished(event):
    LiveSession.objects.filter(
        room_name=event.room.name
    ).update(status=LiveSession.STATUS_COMPLETED)
