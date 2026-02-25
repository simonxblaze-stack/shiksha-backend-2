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

)
from enrollments.models import Enrollment


class ChoiceAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ["id", "text", "is_correct"]


class ChoicePublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ["id", "text"]


class QuestionCreateSerializer(serializers.ModelSerializer):
    choices = ChoiceAdminSerializer(many=True)

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

        if not Enrollment.objects.filter(
            user=user,
            course=quiz.subject.course,
            status=Enrollment.STATUS_ACTIVE
        ).exists():
            raise ValidationError("Not enrolled in this course.")

        if not quiz.is_published:
            raise ValidationError("Quiz not published.")

        if quiz.due_date <= timezone.now():
            raise ValidationError("Quiz expired.")

        if QuizAttempt.objects.filter(
            quiz=quiz,
            student=user,
            status=QuizAttempt.STATUS_SUBMITTED
        ).exists():
            raise ValidationError("Quiz already submitted.")

        if len(attrs["answers"]) != quiz.questions.count():
            raise ValidationError("All questions must be answered.")

        return attrs

    @transaction.atomic
    def save(self, **kwargs):
        quiz = self.context["quiz"]
        user = self.context["request"].user
        submitted_answers = self.validated_data["answers"]

        attempt, _ = QuizAttempt.objects.select_for_update().get_or_create(
            quiz=quiz,
            student=user,
        )

        if attempt.status == QuizAttempt.STATUS_SUBMITTED:
            raise ValidationError("Quiz already submitted.")

        score = 0
        attempt.answers.all().delete()

        for item in submitted_answers:
            question_id = item.get("question")
            choice_id = item.get("selected_choice")

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

            if choice.is_correct:
                score += question.marks

            StudentAnswer.objects.create(
                attempt=attempt,
                question=question,
                selected_choice=choice,
                is_correct=choice.is_correct,
            )

        attempt.score = score
        attempt.status = QuizAttempt.STATUS_SUBMITTED
        attempt.submitted_at = timezone.now()
        attempt.save(update_fields=["score", "status", "submitted_at"])

        return attempt


class QuestionPublicSerializer(serializers.ModelSerializer):
    choices = ChoicePublicSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = [
            "id",
            "text",
            "marks",
            "order",
            "choices",
        ]


class QuizDetailSerializer(serializers.ModelSerializer):
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

    questions = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = [
            "id",
            "title",
            "description",
            "subject_name",
            "course_title",
            "teacher_name",
            "due_date",
            "created_at",
            "time_limit_minutes",
            "questions",
        ]

    def get_questions(self, obj):
        questions = obj.questions.all().order_by("order")
        return QuestionPublicSerializer(questions, many=True).data


class QuestionResultSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    text = serializers.CharField()
    selected_choice = serializers.CharField()
    correct_choice = serializers.CharField()
    is_correct = serializers.BooleanField()


class QuizResultSerializer(serializers.Serializer):
    quiz_id = serializers.UUIDField()
    title = serializers.CharField()
    subject_name = serializers.CharField()
    teacher_name = serializers.CharField()
    total_marks = serializers.IntegerField()
    score = serializers.IntegerField()
    submitted_at = serializers.DateTimeField()
    questions = QuestionResultSerializer(many=True)
