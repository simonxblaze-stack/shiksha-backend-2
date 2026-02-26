from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Profile, Role, UserRole
from courses.models import Course, Subject, Chapter
from payments.models import Order, Payment
from enrollments.models import Enrollment
from assignments.models import Assignment, AssignmentSubmission
from .models import LiveSession, LiveSessionAttendance

from quizzes.models import (
    Quiz,
    Question,
    Choice,
    QuizAttempt,
    StudentAnswer,
)

# =========================
# USER ADMIN
# =========================


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User

    list_display = (
        "email",
        "username",
        "is_verified",
        "is_staff",
        "is_active",
    )

    list_filter = (
        "is_verified",
        "is_staff",
        "is_active",
    )

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("username",)}),
        ("Verification", {"fields": ("is_verified", "verified_at")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_staff",
                    "is_active",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    ordering = ("email",)
    search_fields = ("email", "username")


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user",)


admin.site.register(Role)
admin.site.register(UserRole)

# =========================
# COURSE ADMIN
# =========================


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "created_at")
    search_fields = ("title",)
    list_filter = ("created_at",)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "course", "order", "get_teachers")
    list_filter = ("course",)
    ordering = ("course", "order")
    search_fields = ("name", "course__title")
    filter_horizontal = ("teachers",)

    def get_teachers(self, obj):
        return ", ".join([t.email for t in obj.teachers.all()])

    get_teachers.short_description = "Teachers"


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ("title", "subject", "order")
    list_filter = ("subject",)
    ordering = ("subject", "order")

# =========================
# PAYMENT ADMIN
# =========================


admin.site.register(Order)
admin.site.register(Payment)

# =========================
# ENROLLMENT ADMIN
# =========================


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "status", "enrolled_at")
    list_filter = ("status", "enrolled_at")
    search_fields = ("user__email", "course__title")

# =========================
# ASSIGNMENT ADMIN
# =========================


class AssignmentSubmissionInline(admin.TabularInline):
    model = AssignmentSubmission
    extra = 0
    readonly_fields = ("student", "submitted_file", "submitted_at")


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "chapter",
        "due_date",
        "created_at",
    )
    list_filter = (
        "due_date",
        "chapter__subject__course",
    )
    search_fields = (
        "title",
        "chapter__subject__name",
        "chapter__subject__course__title",
    )
    ordering = ("-created_at",)
    inlines = [AssignmentSubmissionInline]


@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "assignment",
        "student",
        "submitted_at",
    )
    list_filter = (
        "submitted_at",
        "assignment__chapter__subject__course",
    )
    search_fields = (
        "student__email",
        "assignment__title",
    )
    ordering = ("-submitted_at",)

# =========================
# QUIZ ADMIN
# =========================


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    show_change_link = True


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "subject",
        "created_by",
        "is_published",
        "due_date",
        "total_marks",
        "created_at",
    )

    list_filter = (
        "is_published",
        "due_date",
        "subject__course",
        "subject",
    )

    search_fields = (
        "title",
        "created_by__email",
        "subject__name",
        "subject__course__title",
    )

    ordering = ("-created_at",)

    readonly_fields = (
        "created_at",
        "updated_at",
        "total_marks",
    )

    inlines = [QuestionInline]


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 0


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        "quiz",
        "order",
        "marks",
    )

    list_filter = (
        "quiz__subject__course",
        "quiz__subject",
    )

    ordering = ("quiz", "order")

    inlines = [ChoiceInline]


class StudentAnswerInline(admin.TabularInline):
    model = StudentAnswer
    extra = 0
    readonly_fields = (
        "question",
        "selected_choice",
        "is_correct",
    )
    can_delete = False


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "quiz",
        "score",
        "status",
        "submitted_at",
    )

    list_filter = (
        "status",
        "quiz__subject__course",
        "quiz__subject",
    )

    search_fields = (
        "student__email",
        "quiz__title",
    )

    ordering = ("-submitted_at",)

    readonly_fields = (
        "student",
        "quiz",
        "score",
        "status",
        "started_at",
        "submitted_at",
    )

    inlines = [StudentAnswerInline]


@admin.register(StudentAnswer)
class StudentAnswerAdmin(admin.ModelAdmin):
    list_display = (
        "attempt",
        "question",
        "selected_choice",
        "is_correct",
    )

    list_filter = (
        "is_correct",
        "attempt__quiz__subject__course",
    )

    search_fields = (
        "attempt__student__email",
        "question__text",
    )


@admin.register(LiveSession)
class LiveSessionAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "course",
        "subject",
        "created_by",
        "start_time",
        "end_time",
        "status",
    )
    list_filter = ("status", "course", "subject")
    search_fields = ("title", "room_name", "created_by__email")
    readonly_fields = ("room_name",)
    ordering = ("-start_time",)
    actions = ["mark_cancelled"]

    def mark_cancelled(self, request, queryset):
        queryset.update(status=LiveSession.STATUS_CANCELLED)
    mark_cancelled.short_description = "Mark selected sessions as Cancelled"


@admin.register(LiveSessionAttendance)
class LiveSessionAttendanceAdmin(admin.ModelAdmin):
    list_display = (
        "session",
        "user",
        "joined_at",
        "left_at",
        "duration",
    )

    list_filter = ("session",)
    search_fields = ("user__email", "session__title")
    ordering = ("-joined_at",)

    readonly_fields = (
        "session",
        "user",
        "joined_at",
        "left_at",
    )

    def duration(self, obj):
        if obj.joined_at and obj.left_at:
            return obj.left_at - obj.joined_at
        return "—"

    duration.short_description = "Duration"
