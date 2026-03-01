from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Prefetch

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from enrollments.models import Enrollment
from enrollments.permissions import IsEnrolledInCourse

from .models import Assignment, AssignmentSubmission
from .serializers import (
    AssignmentListSerializer,
    AssignmentDetailSerializer,
)


# ==========================================
# ASSIGNMENT DETAIL VIEW
# ==========================================

class AssignmentDetailView(generics.RetrieveAPIView):
    serializer_class = AssignmentDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"
    lookup_url_kwarg = "assignment_id"

    def get_queryset(self):
        user = self.request.user

        submission_prefetch = Prefetch(
            "submissions",
            queryset=AssignmentSubmission.objects.filter(student=user),
            to_attr="user_submission_list",
        )

        queryset = (
            Assignment.objects
            .select_related("chapter__subject__course")
            .prefetch_related(submission_prefetch)
        )

        queryset = list(queryset)

        for obj in queryset:
            obj.user_submission = (
                obj.user_submission_list[0]
                if obj.user_submission_list
                else None
            )

        return queryset

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        course = instance.chapter.subject.course
        subject = instance.chapter.subject
        user = request.user

        # =========================
        # TEACHER ACCESS
        # =========================
        if user.has_role("TEACHER"):
            is_assigned = subject.subject_teachers.filter(
                teacher=user
            ).exists()

            if not is_assigned:
                raise PermissionDenied("Not assigned to this subject.")

        # =========================
        # STUDENT ACCESS
        # =========================
        else:
            if not Enrollment.objects.filter(
                user=user,
                course=course,
                status=Enrollment.STATUS_ACTIVE
            ).exists():
                raise PermissionDenied("Not authorized.")

        serializer = self.get_serializer(instance)
        return Response(serializer.data)


# ==========================================
# SUBMIT ASSIGNMENT VIEW
# ==========================================

class SubmitAssignmentView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = "assignment_id"

    def post(self, request, *args, **kwargs):
        assignment_id = kwargs["assignment_id"]

        assignment = get_object_or_404(
            Assignment.objects.select_related(
                "chapter__subject__course"
            ),
            id=assignment_id,
        )

        # ❌ Only students can submit
        if not request.user.has_role("STUDENT"):
            return Response(
                {"detail": "Only students can submit assignments."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # 🔒 Enrollment check
        if not Enrollment.objects.filter(
            user=request.user,
            course=assignment.chapter.subject.course,
            status=Enrollment.STATUS_ACTIVE
        ).exists():
            return Response(
                {"detail": "Not authorized."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # ⛔ Expired check
        if assignment.due_date < timezone.now():
            return Response(
                {"detail": "Assignment expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file = request.FILES.get("file")

        if not file:
            return Response(
                {"detail": "File required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        AssignmentSubmission.objects.update_or_create(
            assignment=assignment,
            student=request.user,
            defaults={"submitted_file": file},
        )

        return Response(
            {"detail": "Submission successful."},
            status=status.HTTP_200_OK,
        )

# ==========================================
# COURSE ASSIGNMENTS LIST VIEW
# ==========================================


class CourseAssignmentsView(generics.ListAPIView):
    serializer_class = AssignmentListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        course_id = self.kwargs["course_id"]
        user = self.request.user

        submission_prefetch = Prefetch(
            "submissions",
            queryset=AssignmentSubmission.objects.filter(student=user),
            to_attr="user_submission_list",
        )

        # =========================
        # TEACHER ACCESS
        # =========================
        if user.has_role("TEACHER"):
            queryset = Assignment.objects.filter(
                chapter__subject__course__id=course_id,
                chapter__subject__subject_teachers__teacher=user
            )

        # =========================
        # STUDENT ACCESS
        # =========================
        else:
            if not Enrollment.objects.filter(
                user=user,
                course_id=course_id,
                status=Enrollment.STATUS_ACTIVE
            ).exists():
                raise PermissionDenied("Not enrolled.")

            queryset = Assignment.objects.filter(
                chapter__subject__course__id=course_id
            )

        queryset = (
            queryset
            .select_related("chapter__subject__course")
            .prefetch_related(submission_prefetch)
            .distinct()
        )

        queryset = list(queryset)

        for obj in queryset:
            obj.user_submission = (
                obj.user_submission_list[0]
                if obj.user_submission_list
                else None
            )

        return queryset
