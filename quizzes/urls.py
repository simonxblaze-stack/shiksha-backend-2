from django.urls import path

from .views import (
    CreateQuizView,
    AddQuestionView,
    PublishQuizView,
    StudentDashboardView,
    StartQuizView,
    SubmitQuizView,
)

urlpatterns = [

    # -------------------------------
    # 🧑‍🏫 Teacher Routes
    # -------------------------------

    path(
        "quizzes/",
        CreateQuizView.as_view(),
        name="create-quiz",
    ),

    path(
        "quizzes/<uuid:pk>/questions/",
        AddQuestionView.as_view(),
        name="add-question",
    ),

    path(
        "quizzes/<uuid:pk>/publish/",
        PublishQuizView.as_view(),
        name="publish-quiz",
    ),

    # -------------------------------
    # 🎓 Student Routes
    # -------------------------------

    path(
        "student/quizzes/",
        StudentDashboardView.as_view(),
        name="student-dashboard",
    ),

    path(
        "quizzes/<uuid:pk>/start/",
        StartQuizView.as_view(),
        name="start-quiz",
    ),

    path(
        "quizzes/<uuid:pk>/submit/",
        SubmitQuizView.as_view(),
        name="submit-quiz",
    ),
]
