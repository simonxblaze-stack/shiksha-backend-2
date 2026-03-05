from activity.models import Activity
from quizzes.models import Quiz
from assignments.models import Assignment
from rest_framework import serializers
from livestream.models import LiveSession


class DashboardSessionSerializer(serializers.ModelSerializer):

    subject = serializers.CharField(source="subject.name")
    topic = serializers.CharField(source="title")
    teacher = serializers.CharField(source="created_by.email")
    dateTime = serializers.DateTimeField(source="start_time")

    class Meta:
        model = LiveSession
        fields = [
            "id",
            "subject",
            "topic",
            "teacher",
            "dateTime"
        ]


class DashboardAssignmentSerializer(serializers.ModelSerializer):

    teacher = serializers.SerializerMethodField()
    due = serializers.DateTimeField(source="due_date")

    class Meta:
        model = Assignment
        fields = [
            "id",
            "title",
            "teacher",
            "due"
        ]

    def get_teacher(self, obj):

        teacher = obj.chapter.subject.subject_teachers.first()

        if teacher:
            return teacher.teacher.email

        return "Unknown"


class DashboardQuizSerializer(serializers.ModelSerializer):

    teacher = serializers.CharField(source="created_by.email")
    due = serializers.DateTimeField(source="due_date")

    class Meta:
        model = Quiz
        fields = [
            "id",
            "title",
            "teacher",
            "due"
        ]


class DashboardActivitySerializer(serializers.ModelSerializer):

    class Meta:
        model = Activity
        fields = [
            "id",
            "type",
            "title",
            "due_date",
            "created_at"
        ]
