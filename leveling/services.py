from datetime import date, timedelta
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from .models import (
    UserLevelProfile,
    Achievement,
    UserAchievement,
    Quest,
    UserQuest,
)


def get_current_week_boundaries(target_date=None):
    """Returns (start_of_week, end_of_week) as date objects for Monday-Sunday."""
    if target_date is None:
        target_date = timezone.now().date()
    elif isinstance(target_date, timezone.datetime):
        target_date = target_date.date()
    start = target_date - timedelta(days=target_date.weekday())
    end = start + timedelta(days=6)
    return start, end


def seed_default_gamification_content():
    """Seeds or updates the baseline quests and achievements."""
    default_quests = [
        {
            'slug': 'weekly_apply_job',
            'title': 'Weekly Hustle: Apply to a Job',
            'description': 'Submit at least 1 job application this week.',
            'quest_type': 'weekly',
            'metric_key': 'weekly_applications',
            'target_count': 1,
            'xp_reward': 100,
            'icon': 'fa-solid fa-paper-plane',
        },
        {
            'slug': 'weekly_update_profile',
            'title': 'Polish the Resume',
            'description': 'Update your profile details, skills, or headline this week.',
            'quest_type': 'weekly',
            'metric_key': 'profile_updated',
            'target_count': 1,
            'xp_reward': 75,
            'icon': 'fa-solid fa-user-pen',
        },
        {
            'slug': 'weekly_post_job',
            'title': 'Talent Scout: Post a Job',
            'description': 'Publish at least 1 job opening to attract candidates this week.',
            'quest_type': 'weekly',
            'metric_key': 'weekly_job_posted',
            'target_count': 1,
            'xp_reward': 100,
            'icon': 'fa-solid fa-briefcase',
        },
        {
            'slug': 'weekly_review_applicant',
            'title': 'Candidate Reviewer',
            'description': 'Review and update the status of at least 1 applicant this week.',
            'quest_type': 'weekly',
            'metric_key': 'applicant_status_updated',
            'target_count': 1,
            'xp_reward': 75,
            'icon': 'fa-solid fa-user-check',
        },
        {
            'slug': 'weekly_update_company_profile',
            'title': 'Polish Company Profile',
            'description': 'Update your company about us, tagline, or culture details this week.',
            'quest_type': 'weekly',
            'metric_key': 'profile_updated',
            'target_count': 1,
            'xp_reward': 50,
            'icon': 'fa-solid fa-building',
        },
    ]

    for q_data in default_quests:
        Quest.objects.update_or_create(slug=q_data['slug'], defaults=q_data)

    default_achievements = [
        {
            'slug': 'locking_in',
            'title': 'Locking In...',
            'description': 'Create your account and jumpstart your LockedIn journey.',
            'category': 'milestone',
            'icon': 'fa-solid fa-lock-open',
            'xp_reward': 0,
            'target_value': 1,
            'metric_key': 'account_created',
            'is_secret': False,
            'order': 0,
        },
        {
            'slug': 'locked_in',
            'title': 'Locked In.',
            'description': 'Complete your profile setup for the first time.',
            'category': 'milestone',
            'icon': 'fa-solid fa-lock',
            'xp_reward': 0,
            'target_value': 1,
            'metric_key': 'profile_completed',
            'is_secret': False,
            'order': 1,
        },
        {
            'slug': 'first_step',
            'title': 'First Step',
            'description': 'Submit your first job application or list your first position.',
            'category': 'milestone',
            'icon': 'fa-solid fa-shoe-prints',
            'xp_reward': 50,
            'target_value': 1,
            'metric_key': 'total_applications',
            'is_secret': False,
            'order': 2,
        },
        {
            'slug': 'apply_20_jobs',
            'title': 'Job Hunter',
            'description': 'Apply to 20 jobs. Consistency is key!',
            'category': 'milestone',
            'icon': 'fa-solid fa-bullseye',
            'xp_reward': 300,
            'target_value': 20,
            'metric_key': 'total_applications',
            'is_secret': False,
            'order': 3,
        },
        {
            'slug': 'rejected_after_internship',
            'title': 'The Irony',
            'description': 'Get rejected from a job after already having internship experience on your profile.',
            'category': 'novelty',
            'icon': 'fa-solid fa-face-laugh-squint',
            'xp_reward': 250,
            'target_value': 1,
            'metric_key': 'rejected_after_internship',
            'is_secret': True,
            'order': 4,
        },
    ]

    for a_data in default_achievements:
        Achievement.objects.update_or_create(slug=a_data['slug'], defaults=a_data)


def award_account_created_achievement(user):
    """Awards the 'Locking In...' achievement on sign up."""
    seed_default_gamification_content()
    profile = get_or_create_user_level_profile(user)
    ach = Achievement.objects.get(slug='locking_in')
    ua, _ = UserAchievement.objects.get_or_create(user=user, achievement=ach)

    leveled_up = False
    if not ua.unlocked:
        ua.unlocked = True
        ua.unlocked_at = timezone.now()
        ua.current_progress = 1
        ua.viewed = True
        ua.save()
        if ach.xp_reward > 0:
            leveled_up = profile.add_xp(ach.xp_reward)

    return ach, profile, leveled_up


def award_profile_completed_achievement(user):
    """Awards the 'Locked In.' achievement when the user fills out and saves their profile for the first time."""
    seed_default_gamification_content()
    profile = get_or_create_user_level_profile(user)
    try:
        ach = Achievement.objects.get(slug='locked_in')
    except Achievement.DoesNotExist:
        return None

    ua, _ = UserAchievement.objects.get_or_create(user=user, achievement=ach)
    if ua.unlocked:
        return None

    ua.unlocked = True
    ua.unlocked_at = timezone.now()
    ua.current_progress = 1
    ua.viewed = True
    ua.save()
    leveled_up = False
    if ach.xp_reward > 0:
        leveled_up = profile.add_xp(ach.xp_reward)

    return ach, profile, leveled_up


def award_first_step_achievement(user):
    """Awards the 'First Step' achievement (+50 XP) as part of the onboarding tutorial sequence."""
    seed_default_gamification_content()
    profile = get_or_create_user_level_profile(user)
    try:
        ach = Achievement.objects.get(slug='first_step')
    except Achievement.DoesNotExist:
        return None, profile, False

    ua, _ = UserAchievement.objects.get_or_create(user=user, achievement=ach)
    if ua.unlocked:
        return ach, profile, False

    ua.unlocked = True
    ua.unlocked_at = timezone.now()
    ua.current_progress = 1
    ua.viewed = False
    ua.save()
    leveled_up = profile.add_xp(ach.xp_reward)

    return ach, profile, leveled_up



def get_or_create_user_level_profile(user):
    """Retrieves or initializes the user's level profile, syncing baseline stats."""
    profile, created = UserLevelProfile.objects.get_or_create(user=user)
    if created:
        sync_user_stats(user, profile)
    return profile


def sync_user_stats(user, level_profile=None):
    """Recalculates cached counters from existing application records."""
    if level_profile is None:
        level_profile, _ = UserLevelProfile.objects.get_or_create(user=user)

    from jobs.models import JobApplication

    apps = JobApplication.objects.filter(applicant=user).exclude(job__title__icontains='(Demo)')
    total_apps = apps.count()
    distinct_companies = apps.values('job__recruiter').distinct().count()
    interviews = apps.filter(status='interview').count()
    offers = apps.filter(status='offer').count()
    rejections = apps.filter(status='closed').count()

    level_profile.total_applications = total_apps
    level_profile.distinct_companies_applied = distinct_companies
    level_profile.interviews_count = interviews
    level_profile.offers_count = offers
    level_profile.rejections_count = rejections
    level_profile.save()

    return level_profile


def ensure_user_quests(user):
    """Ensures that the user has instances for all active weekly quests for the current week."""
    profile = get_or_create_user_level_profile(user)
    if not profile.tutorial_completed:
        return UserQuest.objects.none()

    seed_default_gamification_content()
    start_date, end_date = get_current_week_boundaries()

    is_employer = hasattr(user, 'profile') and user.profile.role == 'employer'
    if is_employer:
        active_quests = Quest.objects.filter(
            is_active=True,
            quest_type='weekly',
            slug__in=['weekly_post_job', 'weekly_review_applicant', 'weekly_update_company_profile']
        )
    else:
        active_quests = Quest.objects.filter(
            is_active=True,
            quest_type='weekly',
            slug__in=['weekly_apply_job', 'weekly_update_profile']
        )
    user_quests = []

    for quest in active_quests:
        uq, _ = UserQuest.objects.get_or_create(
            user=user,
            quest=quest,
            period_start=start_date,
            defaults={'period_end': end_date}
        )
        user_quests.append(uq)

    return UserQuest.objects.filter(
        user=user,
        period_start=start_date,
        quest__in=active_quests
    ).select_related('quest')


def ensure_user_achievements(user):
    """Ensures user achievement records exist and returns them ordered."""
    seed_default_gamification_content()
    achievements = Achievement.objects.all()

    for ach in achievements:
        UserAchievement.objects.get_or_create(
            user=user,
            achievement=ach
        )

    # Sync milestone progress
    check_achievements(user)

    return UserAchievement.objects.filter(
        user=user
    ).select_related('achievement').order_by('achievement__order')


def check_achievements(user):
    """Evaluates and unlocks any achievements whose criteria have been met."""
    profile = get_or_create_user_level_profile(user)
    unlocked_any = False

    user_achs = UserAchievement.objects.filter(user=user).select_related('achievement')
    for ua in user_achs:
        ach = ua.achievement
        if ua.unlocked:
            continue

        progress = 0
        should_unlock = False

        if ach.metric_key == 'total_applications':
            progress = profile.total_applications
            if progress >= ach.target_value:
                should_unlock = True

        elif ach.metric_key == 'rejected_after_internship':
            # Evaluated specifically in status change, but can also verify here
            if check_has_internship(user) and profile.rejections_count > 0:
                progress = 1
                should_unlock = True

        ua.current_progress = min(progress, ach.target_value)
        if should_unlock:
            ua.unlocked = True
            ua.unlocked_at = timezone.now()
            ua.current_progress = ach.target_value
            profile.add_xp(ach.xp_reward)
            unlocked_any = True

        ua.save()

    return unlocked_any


def check_has_internship(user):
    """Checks if the user has an internship listed in Experiences or Education."""
    try:
        from accounts.models import Experience
        experiences = Experience.objects.filter(profile__user=user)
        for exp in experiences:
            combined = f"{exp.title} {exp.description}".lower()
            if 'intern' in combined or 'internship' in combined:
                return True
    except Exception:
        pass
    return False


def record_job_applied(user, job_application):
    """Event handler when a user applies to a job."""
    with transaction.atomic():
        profile = get_or_create_user_level_profile(user)

        # For demo jobs: complete the "First Step" achievement as part of the tutorial sequence
        is_demo = job_application and job_application.job and '(Demo)' in job_application.job.title
        if is_demo:
            award_first_step_achievement(user)
            return

        if not profile.tutorial_completed:
            return

        sync_user_stats(user, profile)

        # Update weekly application quest
        start_date, end_date = get_current_week_boundaries()
        apply_quests = Quest.objects.filter(metric_key='weekly_applications', is_active=True)
        for q in apply_quests:
            uq, _ = UserQuest.objects.get_or_create(
                user=user,
                quest=q,
                period_start=start_date,
                defaults={'period_end': end_date}
            )
            if not uq.is_completed:
                uq.progress += 1
                if uq.progress >= q.target_count:
                    uq.is_completed = True
                    uq.completed_at = timezone.now()
                uq.save()

        # Check achievements
        check_achievements(user)


def record_application_status_change(application, old_status, new_status):
    """Event handler when an employer updates an application's status."""
    applicant = application.applicant
    with transaction.atomic():
        profile = get_or_create_user_level_profile(applicant)
        sync_user_stats(applicant, profile)

        # If rejected/closed
        if new_status == 'closed':
            # Check for novelty achievement "rejected_after_internship"
            if check_has_internship(applicant):
                try:
                    irony_ach = Achievement.objects.get(slug='rejected_after_internship')
                    ua, _ = UserAchievement.objects.get_or_create(
                        user=applicant,
                        achievement=irony_ach
                    )
                    if not ua.unlocked:
                        ua.unlocked = True
                        ua.unlocked_at = timezone.now()
                        ua.current_progress = 1
                        ua.save()
                        profile.add_xp(irony_ach.xp_reward)
                except Achievement.DoesNotExist:
                    pass

        check_achievements(applicant)


def record_profile_update(user):
    """Event handler when a user updates their profile or adds a skill/experience."""
    with transaction.atomic():
        profile = get_or_create_user_level_profile(user)
        profile.profile_updates_count += 1
        profile.save(update_fields=['profile_updates_count'])

        # Quests do not progress during the onboarding tutorial
        if not profile.tutorial_completed:
            return

        # Update weekly quest
        start_date, end_date = get_current_week_boundaries()
        update_quests = Quest.objects.filter(metric_key='profile_updated', is_active=True)
        for q in update_quests:
            uq, _ = UserQuest.objects.get_or_create(
                user=user,
                quest=q,
                period_start=start_date,
                defaults={'period_end': end_date}
            )
            if not uq.is_completed:
                uq.progress += 1
                if uq.progress >= q.target_count:
                    uq.is_completed = True
                    uq.completed_at = timezone.now()
                uq.save()

        check_achievements(user)


def record_job_posted(user, job_posting):
    """Event handler when an employer posts a job opening."""
    with transaction.atomic():
        profile = get_or_create_user_level_profile(user)

        # Demo jobs don't count towards weekly quests
        if job_posting and '(Demo)' in job_posting.title:
            return

        if not profile.tutorial_completed:
            return

        start_date, end_date = get_current_week_boundaries()
        post_quests = Quest.objects.filter(metric_key='weekly_job_posted', is_active=True)
        for q in post_quests:
            uq, _ = UserQuest.objects.get_or_create(
                user=user,
                quest=q,
                period_start=start_date,
                defaults={'period_end': end_date}
            )
            if not uq.is_completed:
                uq.progress += 1
                if uq.progress >= q.target_count:
                    uq.is_completed = True
                    uq.completed_at = timezone.now()
                uq.save()


def record_applicant_status_updated(recruiter, application):
    """Event handler when an employer reviews and updates an applicant's status."""
    with transaction.atomic():
        profile = get_or_create_user_level_profile(recruiter)

        if application and application.job and '(Demo)' in application.job.title:
            award_first_step_achievement(recruiter)
            return

        if not profile.tutorial_completed:
            return

        start_date, end_date = get_current_week_boundaries()
        review_quests = Quest.objects.filter(metric_key='applicant_status_updated', is_active=True)
        for q in review_quests:
            uq, _ = UserQuest.objects.get_or_create(
                user=recruiter,
                quest=q,
                period_start=start_date,
                defaults={'period_end': end_date}
            )
            if not uq.is_completed:
                uq.progress += 1
                if uq.progress >= q.target_count:
                    uq.is_completed = True
                    uq.completed_at = timezone.now()
                uq.save()


def claim_quest_reward(user, user_quest_id):
    """Claims the XP reward for a completed UserQuest."""
    with transaction.atomic():
        try:
            uq = UserQuest.objects.select_for_update().get(id=user_quest_id, user=user)
        except UserQuest.DoesNotExist:
            return False, "Quest not found.", False

        if not uq.is_completed:
            return False, "Quest is not completed yet.", False

        if uq.is_reward_claimed:
            return False, "Reward has already been claimed.", False

        uq.is_reward_claimed = True
        uq.claimed_at = timezone.now()
        uq.save(update_fields=['is_reward_claimed', 'claimed_at'])

        profile = get_or_create_user_level_profile(user)
        leveled_up = profile.add_xp(uq.quest.xp_reward)

        return True, f"Claimed {uq.quest.xp_reward} XP!", leveled_up

