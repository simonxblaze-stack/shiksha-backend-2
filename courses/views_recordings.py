from django.conf import settings
import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models_recordings import SessionRecording
from .serializers_recordings import SessionRecordingSerializer
from .models import Subject
from accounts.permissions import IsTeacher


class SubjectRecordingsView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, subject_id):

        subject = get_object_or_404(Subject, id=subject_id)

        recordings = SessionRecording.objects.filter(
            subject=subject,
            is_published=True
        )

        serializer = SessionRecordingSerializer(recordings, many=True)

        return Response(serializer.data)


class CreateRecordingView(APIView):

    permission_classes = [IsAuthenticated, IsTeacher]

    def post(self, request, subject_id):

        subject = get_object_or_404(Subject, id=subject_id)

        serializer = SessionRecordingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.save(
            subject=subject,
            uploaded_by=request.user
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class DeleteRecordingView(APIView):

    permission_classes = [IsAuthenticated, IsTeacher]

    def delete(self, request, recording_id):

        recording = get_object_or_404(SessionRecording, id=recording_id)

        recording.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class CreateVideoSlotView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        title = request.data.get("title")

        url = f"https://video.bunnycdn.com/library/{settings.BUNNY_LIBRARY_ID}/videos"

        headers = {
            "AccessKey": settings.BUNNY_API_KEY,
            "Content-Type": "application/json"
        }

        payload = {
            "title": title
        }

        r = requests.post(url, json=payload, headers=headers)

        if r.status_code not in [200, 201]:
            return Response({"error": r.text}, status=500)

        data = r.json()

        return Response({
            "video_id": data["guid"]
        })


class SaveRecordingView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, subject_id):

        subject = get_object_or_404(Subject, id=subject_id)

        recording = SessionRecording.objects.create(
            subject=subject,
            title=request.data.get("title"),
            session_date=request.data.get("session_date"),
            duration=request.data.get("duration"),
            bunny_video_id=request.data.get("video_id"),
            uploaded_by=request.user,
        )

        return Response(SessionRecordingSerializer(recording).data)
