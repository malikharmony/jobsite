from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from accounts.models import Profile, Experience
from jobs.models import JobPosting, JobApplication
from leveling.models import (
    UserLevelProfile,
    Achievement,
    UserAchievement,
    Quest,
    UserQuest,
)
from leveling.services import (
    seed_default_gamification_content,
    get_or_create_user_level_profile,
    ensure_user_quests,
    ensure_user_achievements,
    claim_quest_reward,
    get_current_week_boundaries,
)


class LevelingFrameworkTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Recruiter
        self.recruiter = User.objects.create_user(
            username='recruiter_jane',
            email='recruiter@example.com',
            password='password123'
        )
        Profile.objects.create(user=self.recruiter, role='employer')

        # Job seeker
        self.applicant = User.objects.create_user(
            username='applicant_bob',
            email='applicant@example.com',
            password='password123'
        )
        self.profile = Profile.objects.create(user=self.applicant, role='job_seeker')

        # Seed content
        seed_default_gamification_content()

        # Job Posting
        self.job1 = JobPosting.objects.create(
            title='Software Engineer',
            description='Build cool things',
            recruiter=self.recruiter,
            work_type='remote',
            required_skills='Python, Django',
            location='Atlanta, GA',
            salary_min=80000,
            salary_max=120000,
            status='active'
        )

        self.job2 = JobPosting.objects.create(
            title='Data Analyst',
            description='Analyze data',
            recruiter=self.recruiter,
            work_type='hybrid',
            required_skills='SQL, Python',
            location='Remote',
            salary_min=70000,
            salary_max=95000,
            status='active'
        )

    def test_level_profile_xp_and_level_calculation(self):
        profile = get_or_create_user_level_profile(self.applicant)
        self.assertEqual(profile.level, 1)
        self.assertEqual(profile.xp, 0)
        self.assertEqual(profile.rank_title, "Job Seeker Novice")

        # Add 120 XP -> Should cross level 2 (threshold: 100 XP)
        leveled_up = profile.add_xp(120)
        self.assertTrue(leveled_up)
        self.assertEqual(profile.level, 2)
        self.assertEqual(profile.rank_title, "Resume Ready")
        self.assertEqual(profile.xp_progress_in_current_level, 20)
        self.assertEqual(profile.xp_needed_for_next_level, 150) # Level 3 is 250 (250 - 100 = 150)

    def test_job_application_triggers_quest_and_first_step_achievement(self):
        # Initial state
        ensure_user_quests(self.applicant)
        ensure_user_achievements(self.applicant)

        # Apply to job1
        app = JobApplication.objects.create(
            job=self.job1,
            applicant=self.applicant,
            cover_letter="I am very excited about this role!"
        )

        level_profile = UserLevelProfile.objects.get(user=self.applicant)
        self.assertEqual(level_profile.total_applications, 1)

        # "First Step" achievement should be unlocked (+50 XP)
        first_step = Achievement.objects.get(slug='first_step')
        ua = UserAchievement.objects.get(user=self.applicant, achievement=first_step)
        self.assertTrue(ua.unlocked)
        self.assertEqual(level_profile.xp, 50)

        # Weekly quest "weekly_apply_job" should be completed
        start_date, _ = get_current_week_boundaries()
        weekly_apply_quest = Quest.objects.get(slug='weekly_apply_job')
        uq = UserQuest.objects.get(user=self.applicant, quest=weekly_apply_quest, period_start=start_date)
        self.assertTrue(uq.is_completed)
        self.assertFalse(uq.is_reward_claimed)

        # Claim the quest reward
        success, msg, leveled_up = claim_quest_reward(self.applicant, uq.id)
        self.assertTrue(success)
        uq.refresh_from_db()
        self.assertTrue(uq.is_reward_claimed)

        # XP should now be 50 + 100 = 150 XP -> Level 2 reached!
        level_profile.refresh_from_db()
        self.assertEqual(level_profile.xp, 150)
        self.assertEqual(level_profile.level, 2)

    def test_novelty_achievement_rejected_after_internship(self):
        ensure_user_achievements(self.applicant)

        # Add internship experience to profile
        Experience.objects.create(
            profile=self.profile,
            title='Software Engineering Intern',
            company='Tech Corp',
            period='Summer 2025',
            description='Developed backend features using Python and Django.'
        )

        # Apply to job
        app = JobApplication.objects.create(
            job=self.job1,
            applicant=self.applicant
        )

        irony_ach = Achievement.objects.get(slug='rejected_after_internship')
        ua = UserAchievement.objects.get(user=self.applicant, achievement=irony_ach)
        self.assertFalse(ua.unlocked)

        # Recruiter marks application closed (rejection)
        app.status = 'closed'
        app.save()

        # Novelty achievement "The Irony" should now be unlocked!
        ua.refresh_from_db()
        self.assertTrue(ua.unlocked)

        level_profile = UserLevelProfile.objects.get(user=self.applicant)
        self.assertGreaterEqual(level_profile.xp, irony_ach.xp_reward)

    def test_profile_update_quest(self):
        ensure_user_quests(self.applicant)
        start_date, _ = get_current_week_boundaries()
        update_quest = Quest.objects.get(slug='weekly_update_profile')
        uq = UserQuest.objects.get(user=self.applicant, quest=update_quest, period_start=start_date)
        self.assertFalse(uq.is_completed)

        # Update profile
        self.profile.headline = "Passionate Full-Stack Developer"
        self.profile.save()

        uq.refresh_from_db()
        self.assertTrue(uq.is_completed)

    def test_apply_20_jobs_achievement_progress(self):
        ensure_user_achievements(self.applicant)
        ach_20 = Achievement.objects.get(slug='apply_20_jobs')
        ua = UserAchievement.objects.get(user=self.applicant, achievement=ach_20)
        self.assertFalse(ua.unlocked)

        # Create multiple jobs and apply
        for i in range(20):
            job = JobPosting.objects.create(
                title=f'Job {i}',
                description='Desc',
                recruiter=self.recruiter,
                work_type='remote',
                required_skills='Python',
                location='Online',
                salary_min=60000,
                salary_max=90000,
                status='active'
            )
            JobApplication.objects.create(job=job, applicant=self.applicant)

        ua.refresh_from_db()
        self.assertTrue(ua.unlocked)
        self.assertEqual(ua.current_progress, 20)

    def test_dashboard_view(self):
        # Anonymous user redirected to login
        response = self.client.get(reverse('leveling:dashboard'))
        self.assertEqual(response.status_code, 302)

        # Logged in applicant can access dashboard
        self.client.login(username='applicant_bob', password='password123')
        response = self.client.get(reverse('leveling:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Quests & Leveling')
        self.assertContains(response, 'Weekly Quests')
        self.assertContains(response, 'Badges & Achievements')
        self.assertContains(response, 'Job Seeker Novice')
