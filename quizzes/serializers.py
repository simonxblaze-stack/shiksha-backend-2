import uuid
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import (
    Quiz,
    Question,
    Choice,
    QuizAttempt,
    StudentAnswer,
    SubjectTeacher,
)
from enrollments.models import Enrollment


class ChoiceSerializer(serializers.ModelSerializer):

    class Meta:
        model = Choice
        fields = ["id", "text", "is_correct"]
        read_only_fields = ["id"]


class QuestionCreateSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True)

    class Meta:
        model = Question
        fields = ["id", "text", "marks", "order", "choices"]
        read_only_fields = ["id"]

    def validate_choices(self, value):
        if len(value) < 2:
            raise ValidationError("At least two choices required.")
        return value

    def validate(self, attrs):
        choices = attrs.get("choices", [])
        correct_count = sum(
            1 for c in choices if c.get("is_correct")
        )

        if correct_count != 1:
            raise ValidationError(
                "Exactly one correct answer required."
            )

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        choices_data = validated_data.pop("choices")
        quiz = self.context.get("quiz")

        question = Question.objects.create(
            quiz=quiz,
            **validated_data
        )

        for choice_data in choices_data:
            Choice.objects.create(
                question=question,
                **choice_data
            )

        return question


class QuizCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Quiz
        fields = [
            "id",
            "subject",
            "title",
            "description",
            "due_date",
            "time_limit_minutes",
            "is_published",
        ]
        read_only_fields = ["id"]

    def validate_subject(self, subject):
        user = self.context["request"].user

        if not user.has_role("teacher"):
            raise ValidationError("Only teachers can create quizzes.")

        if not SubjectTeacher.objects.filter(
            subject=subject,
            teacher=user
        ).exists():
            raise ValidationError(
                "You are not assigned to this subject."
            )

        return subject

    def validate_due_date(self, due_date):
        if due_date <= timezone.now():
            raise ValidationError("Due date must be in future.")
        return due_date

    def create(self, validated_data):
        return Quiz.objects.create(
            created_by=self.context["request"].user,
            **validated_data
        )


class QuizDashboardSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(
        source="subject.name",
        read_only=True
    )
    course_title = serializers.CharField(
        source="subject.course.title",
        read_only=True
    )
    teacher_name = serializers.CharField(
        source="created_by.profile.full_name",
        read_only=True
    )

    status = serializers.SerializerMethodField()
    score = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = [
            "id",
            "title",
            "subject_name",
            "course_title",
            "teacher_name",
            "due_date",
            "total_marks",
            "status",
            "score",
        ]

    def get_status(self, obj):
        user = self.context["request"].user

        attempt = QuizAttempt.objects.filter(
            quiz=obj,
            student=user
        ).first()

        if not attempt:
            return "PENDING"

        return attempt.status

    def get_score(self, obj):
        user = self.context["request"].user

        attempt = QuizAttempt.objects.filter(
            quiz=obj,
            student=user,
            status=QuizAttempt.STATUS_SUBMITTED
        ).first()

        return attempt.score if attempt else None


class QuizSubmitSerializer(serializers.Serializer):
    answers = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False
    )

    def validate(self, attrs):
        quiz = self.context["quiz"]
        user = self.context["request"].user

        # Enrollment validation
        if not Enrollment.objects.filter(
            user=user,
            course=quiz.subject.course,
            status=Enrollment.STATUS_ACTIVE
        ).exists():
            raise ValidationError("Not enrolled in this course.")

        # Published validation
        if not quiz.is_published:
            raise ValidationError("Quiz not published.")

        # Expiry validation
        if quiz.due_date <= timezone.now():
            raise ValidationError("Quiz expired.")

        # Prevent double submission
        if QuizAttempt.objects.filter(
            quiz=quiz,
            student=user,
            status=QuizAttempt.STATUS_SUBMITTED
        ).exists():
            raise ValidationError("Quiz already submitted.")

        return attrs

    @transaction.atomic
    def save(self, **kwargs):
        quiz = self.context["quiz"]
        user = self.context["request"].user
        submitted_answers = self.validated_data["answers"]

        # Lock row to prevent race condition
        attempt, created = QuizAttempt.objects.select_for_update().get_or_create(
            quiz=quiz,
            student=user,
        )

        if attempt.status == QuizAttempt.STATUS_SUBMITTED:
            raise ValidationError("Quiz already submitted.")

        score = 0

        # Safety: clear any existing answers
        attempt.answers.all().delete()

        for item in submitted_answers:
            question_id = item.get("question_id")
            choice_id = item.get("choice_id")

            try:
                question = Question.objects.get(
                    id=question_id,
                    quiz=quiz
                )
            except Question.DoesNotExist:
                raise ValidationError("Invalid question.")

            try:
                choice = Choice.objects.get(
                    id=choice_id,
                    question=question
                )
            except Choice.DoesNotExist:
                raise ValidationError("Invalid choice.")

            is_correct = choice.is_correct

            if is_correct:
                score += question.marks

            StudentAnswer.objects.create(
                attempt=attempt,
                question=question,
                selected_choice=choice,
                is_correct=is_correct,
            )

        attempt.score = score
        attempt.status = QuizAttempt.STATUS_SUBMITTED
        attempt.submitted_at = timezone.now()
        attempt.save(update_fields=["score", "status", "submitted_at"])

        return attempt
