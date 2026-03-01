from django.urls import path

from .views import (
    CreateQuizView,
    AddQuestionView,
    PublishQuizView,
    StudentDashboardView,
    StartQuizView,
    SubmitQuizView,
    QuizDetailView,
    QuizResultView,
    StudentQuizSubjectsView,
    TeacherDeleteQuizView
)

urlpatterns = [

    # Teacher
    path("teacher/quizzes/", CreateQuizView.as_view()),
    path("teacher/quizzes/<uuid:pk>/questions/", AddQuestionView.as_view()),
    path("teacher/quizzes/<uuid:pk>/publish/", PublishQuizView.as_view()),
    path("teacher/quizzes/<uuid:pk>/delete/", TeacherDeleteQuizView.as_view()),
    path("teacher/subjects/<uuid:subject_id>/quizzes/",
         TeacherSubjectQuizListView.as_view()),
    path("teacher/quizzes/<uuid:pk>/attempts/",
         TeacherQuizAttemptsView.as_view()),

    # Student
    path("student/quizzes/", StudentDashboardView.as_view()),
    path("quizzes/<uuid:pk>/start/", StartQuizView.as_view()),
    path("quizzes/<uuid:pk>/submit/", SubmitQuizView.as_view()),
    path("quizzes/<uuid:pk>/", QuizDetailView.as_view()),
    path("quizzes/<uuid:pk>/result/", QuizResultView.as_view()),
]
