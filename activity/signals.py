from livestream.models import LiveSession
from quizzes.models import Quiz
from django.db.models.signals import post_save
from django.dispatch import receiver

from assignments.models import Assignment
from enrollments.models import Enrollment
from .services import create_activity
from .models import Activity


@receiver(post_save, sender=Assignment)
def assignment_created(sender, instance, created, **kwargs):

    if not created:
        return

    course = instance.chapter.subject.course

    students = Enrollment.objects.filter(
        course=course,
        status=Enrollment.STATUS_ACTIVE
    ).values_list("user", flat=True)

    for student_id in students:
        create_activity(
            user=student_id,
            obj=instance,
            type=Activity.TYPE_ASSIGNMENT,
            title=f"New assignment: {instance.title}",
            due_date=instance.due_date
        )


@receiver(post_save, sender=Quiz)
def quiz_published(sender, instance, created, **kwargs):

    if not instance.is_published:
        return

    course = instance.subject.course

    students = Enrollment.objects.filter(
        course=course,
        status=Enrollment.STATUS_ACTIVE
    ).values_list("user", flat=True)

    for student_id in students:
        create_activity(
            user=student_id,
            obj=instance,
            type=Activity.TYPE_QUIZ,
            title=f"Quiz available: {instance.title}",
            due_date=instance.due_date
        )


@receiver(post_save, sender=LiveSession)
def session_created(sender, instance, created, **kwargs):

    if not created:
        return

    course = instance.course

    students = Enrollment.objects.filter(
        course=course,
        status=Enrollment.STATUS_ACTIVE
    ).values_list("user", flat=True)

    for student_id in students:
        create_activity(
            user=student_id,
            obj=instance,
            type=Activity.TYPE_SESSION,
            title=f"Live session scheduled: {instance.title}",
            due_date=instance.start_time
        )
