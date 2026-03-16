from courses.models import Subject
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404

from .models import StudyMaterial, MaterialFile
from .serializers import StudyMaterialSerializer
from courses.models import Chapter


# ===============================
# LIST MATERIALS OF A CHAPTER
# ===============================

class ChapterMaterials(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, chapter_id):

        chapter = get_object_or_404(Chapter, id=chapter_id)

        materials = (
            StudyMaterial.objects
            .filter(chapter=chapter)
            .prefetch_related("files")
            .order_by("-created_at")
        )

        serializer = StudyMaterialSerializer(materials, many=True)

        return Response(serializer.data)


# ===============================
# UPLOAD STUDY MATERIAL
# ===============================

class UploadStudyMaterial(APIView):

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, chapter_id):

        chapter = get_object_or_404(Chapter, id=chapter_id)

        material = StudyMaterial.objects.create(
            chapter=chapter,
            title=request.data.get("title"),
            description=request.data.get("description", ""),
            uploaded_by=request.user
        )

        files = request.FILES.getlist("files")

        for file in files:
            MaterialFile.objects.create(
                material=material,
                file=file
            )

        serializer = StudyMaterialSerializer(material)

        return Response(serializer.data, status=status.HTTP_201_CREATED)


# ===============================
# DELETE MATERIAL
# ===============================

class DeleteStudyMaterial(APIView):

    permission_classes = [IsAuthenticated]

    def delete(self, request, material_id):

        material = get_object_or_404(StudyMaterial, id=material_id)

        material.delete()

        return Response(
            {"detail": "Material deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )


# ===============================
# LIST MATERIALS OF A CHAPTER
# ===============================

class ChapterMaterials(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, chapter_id):

        chapter = get_object_or_404(Chapter, id=chapter_id)

        materials = (
            StudyMaterial.objects
            .filter(chapter=chapter)
            .prefetch_related("files")
            .order_by("-created_at")
        )

        serializer = StudyMaterialSerializer(materials, many=True)

        return Response(serializer.data)


# ===============================
# UPLOAD STUDY MATERIAL
# ===============================

class UploadStudyMaterial(APIView):

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, chapter_id):

        chapter = get_object_or_404(Chapter, id=chapter_id)

        title = request.data.get("title")
        files = request.FILES.getlist("files")

        if not title:
            return Response(
                {"detail": "Title is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not files:
            return Response(
                {"detail": "At least one file is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        material = StudyMaterial.objects.create(
            chapter=chapter,
            title=title,
            description=request.data.get("description", ""),
            uploaded_by=request.user
        )

        for file in files:
            MaterialFile.objects.create(
                material=material,
                file=file
            )

        serializer = StudyMaterialSerializer(material)

        return Response(serializer.data, status=status.HTTP_201_CREATED)


# ===============================
# DELETE MATERIAL
# ===============================

class DeleteStudyMaterial(APIView):

    permission_classes = [IsAuthenticated]

    def delete(self, request, material_id):

        material = get_object_or_404(StudyMaterial, id=material_id)

        material.delete()

        return Response(
            {"detail": "Material deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )


# ===============================
# LIST MATERIALS OF A SUBJECT
# ===============================

class SubjectMaterials(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, subject_id):

        subject = get_object_or_404(Subject, id=subject_id)

        materials = (
            StudyMaterial.objects
            .filter(chapter__subject=subject)
            .prefetch_related("files")
            .order_by("-created_at")
        )

        serializer = StudyMaterialSerializer(materials, many=True)

        return Response(serializer.data)


# material tih app hi study material upload na app anita tah hian teacher ho upload na awm a api a awm a tacher ho in an upload tawh list view na a awm bawk a...chuan
# Student side ah anfrotend end code ah student ho tana a student mater subject wise a view na API ( eg. views siam sak ve a ngai)


class StudentSubjectMaterials(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, subject_id):

        subject = get_object_or_404(Subject, id=subject_id)

        materials = (
            StudyMaterial.objects
            .filter(chapter__subject=subject)
            .select_related("chapter")
            .prefetch_related("files")
            .order_by("-created_at")
        )

        serializer = StudyMaterialSerializer(materials, many=True)

        return Response(serializer.data)
