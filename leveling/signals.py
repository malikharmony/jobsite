from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from jobs.models import JobApplication
from accounts.models import Profile, Experience, Education, Skill
from .services import (
    record_job_applied,
    record_application_status_change,
    record_profile_update,
)


@receiver(pre_save, sender=JobApplication)
def track_application_pre_save(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            instance._old_status = old.status
        except sender.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=JobApplication)
def handle_application_post_save(sender, instance, created, **kwargs):
    if created:
        record_job_applied(instance.applicant, instance)
    else:
        old_status = getattr(instance, '_old_status', None)
        if old_status and old_status != instance.status:
            record_application_status_change(instance, old_status, instance.status)


@receiver(post_save, sender=Profile)
def handle_profile_post_save(sender, instance, created, **kwargs):
    if not created:
        record_profile_update(instance.user)


@receiver(post_save, sender=Experience)
def handle_experience_post_save(sender, instance, created, **kwargs):
    record_profile_update(instance.profile.user)


@receiver(post_save, sender=Education)
def handle_education_post_save(sender, instance, created, **kwargs):
    record_profile_update(instance.profile.user)


@receiver(post_save, sender=Skill)
def handle_skill_post_save(sender, instance, created, **kwargs):
    record_profile_update(instance.profile.user)

