from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.exceptions import ValidationError

from accounts.permissions import IsEmailVerified
from enrollments.models import Enrollment

from .models import Quiz, QuizAttempt, SubjectTeacher
from .serializers import (
    QuizCreateSerializer,
    QuestionCreateSerializer,
    QuizDashboardSerializer,
    QuizSubmitSerializer,
)from django.shortcuts import render


class CreateQuizView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsEmailVerified,
    ]

    def post(self, request):
        # Teacher role check
        if not request.user.has_role("teacher"):
            raise ValidationError("Only teachers can create quizzes.")

        subject_id = request.data.get("subject")
        if not subject_id:
            raise ValidationError("Subject is required.")

        # Subject assignment check
        if not SubjectTeacher.objects.filter(
            subject_id=subject_id,
            teacher=request.user
        ).exists():
            raise ValidationError(
                "You are not assigned to this subject."
            )

        serializer = QuizCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        quiz = serializer.save()

        return Response(
            {
                "id": quiz.id,
                "detail": "Quiz created successfully."
            },
            status=status.HTTP_201_CREATED,
        )


class AddQuestionView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsEmailVerified,
    ]

    def post(self, request, pk):
        quiz = get_object_or_404(Quiz, pk=pk)

        if not request.user.has_role("teacher"):
            raise ValidationError("Only teachers allowed.")

        if quiz.created_by != request.user:
            raise ValidationError("Not authorized for this quiz.")

        if quiz.is_published:
            raise ValidationError("Cannot modify published quiz.")

        serializer = QuestionCreateSerializer(
            data=request.data,
            context={"quiz": quiz},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"detail": "Question added successfully."},
            status=status.HTTP_201_CREATED,
        )


class PublishQuizView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsEmailVerified,
    ]

    def patch(self, request, pk):
        quiz = get_object_or_404(Quiz, pk=pk)

        if not request.user.has_role("teacher"):
            raise ValidationError("Only teachers allowed.")

        if quiz.created_by != request.user:
            raise ValidationError("Not authorized.")

        if quiz.is_published:
            raise ValidationError("Quiz already published.")

        if quiz.questions.count() == 0:
            raise ValidationError("Cannot publish empty quiz.")

        total_marks = sum(q.marks for q in quiz.questions.all())

        quiz.total_marks = total_marks
        quiz.is_published = True
        quiz.save(update_fields=["total_marks", "is_published"])

        return Response(
            {"detail": "Quiz published successfully."},
            status=status.HTTP_200_OK,
        )


class StudentDashboardView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsEmailVerified,
    ]

    def get(self, request):
        status_filter = request.query_params.get("status")

        quizzes = Quiz.objects.filter(
            subject__course__enrollments__user=request.user,
            subject__course__enrollments__status=Enrollment.STATUS_ACTIVE,
            is_published=True,
        ).select_related(
            "subject",
            "subject__course",
            "created_by",
            "created_by__profile",
        ).distinct()

        submitted_ids = QuizAttempt.objects.filter(
            student=request.user,
            status=QuizAttempt.STATUS_SUBMITTED,
        ).values_list("quiz_id", flat=True)

        if status_filter == "completed":
            quizzes = quizzes.filter(id__in=submitted_ids)
        elif status_filter == "pending":
            quizzes = quizzes.exclude(id__in=submitted_ids)

        serializer = QuizDashboardSerializer(
            quizzes,
            many=True,
            context={"request": request},
        )

        return Response(serializer.data)


class StartQuizView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsEmailVerified,
    ]

    def post(self, request, pk):
        quiz = get_object_or_404(
            Quiz.objects.select_related("subject__course"),
            pk=pk,
            is_published=True,
        )

        # Enrollment check
        if not Enrollment.objects.filter(
            user=request.user,
            course=quiz.subject.course,
            status=Enrollment.STATUS_ACTIVE,
        ).exists():
            raise ValidationError("Not enrolled in this course.")

        # Expiry check
        if quiz.due_date <= timezone.now():
            raise ValidationError("Quiz expired.")

        attempt, created = QuizAttempt.objects.get_or_create(
            quiz=quiz,
            student=request.user,
        )

        if attempt.status == QuizAttempt.STATUS_SUBMITTED:
            raise ValidationError("Quiz already submitted.")

        return Response(
            {"detail": "Quiz started successfully."},
            status=status.HTTP_200_OK,
        )


class SubmitQuizView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsEmailVerified,
    ]

    def post(self, request, pk):
        quiz = get_object_or_404(
            Quiz.objects.select_related("subject__course"),
            pk=pk,
        )

        serializer = QuizSubmitSerializer(
            data=request.data,
            context={
                "request": request,
                "quiz": quiz,
            },
        )
        serializer.is_valid(raise_exception=True)

        attempt = serializer.save()

        return Response(
            {
                "detail": "Quiz submitted successfully.",
                "score": attempt.score,
                "total_marks": quiz.total_marks,
            },
            status=status.HTTP_200_OK,
        )

# Create your views here.
