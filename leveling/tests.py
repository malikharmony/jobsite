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
        level_profile = get_or_create_user_level_profile(self.applicant)
        level_profile.tutorial_completed = True
        level_profile.save()

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

    def test_unviewed_achievements_api_and_marking_viewed(self):
        # Anonymous redirected
        response = self.client.get(reverse('leveling:api_unviewed'))
        self.assertEqual(response.status_code, 302)

        self.client.login(username='applicant_bob', password='password123')
        ensure_user_achievements(self.applicant)

        # Initially no unviewed unlocked achievements
        res = self.client.get(reverse('leveling:api_unviewed'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['achievements'], [])

        # Trigger first step achievement
        JobApplication.objects.create(job=self.job1, applicant=self.applicant)

        # Now API should return the unlocked achievement
        res = self.client.get(reverse('leveling:api_unviewed'))
        self.assertEqual(res.status_code, 200)
        achievements = res.json()['achievements']
        self.assertEqual(len(achievements), 1)
        ach_data = achievements[0]
        self.assertEqual(ach_data['title'], 'First Step')

        # Mark as viewed
        mark_res = self.client.get(reverse('leveling:api_mark_viewed', kwargs={'user_achievement_id': ach_data['id']}))
        self.assertEqual(mark_res.status_code, 200)
        self.assertTrue(mark_res.json()['success'])

        # Now API should return empty list
        res_after = self.client.get(reverse('leveling:api_unviewed'))
        self.assertEqual(res_after.json()['achievements'], [])

    def test_context_processor_toast_in_html(self):
        self.client.login(username='applicant_bob', password='password123')
        ensure_user_achievements(self.applicant)

        # Unlock achievement
        JobApplication.objects.create(job=self.job1, applicant=self.applicant)

        # Visiting jobs index should include the toast
        res = self.client.get(reverse('jobs.index'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'achievement-toast')
        self.assertContains(res, 'Achievement Unlocked!')
        self.assertContains(res, 'First Step')

    def test_quest_completion_toast_and_api(self):
        self.client.login(username='applicant_bob', password='password123')
        ensure_user_quests(self.applicant)

        # Complete weekly application quest
        JobApplication.objects.create(job=self.job1, applicant=self.applicant)

        # Check API returns the completed quest
        res = self.client.get(reverse('leveling:api_unviewed'))
        self.assertEqual(res.status_code, 200)
        quests = res.json().get('quests', [])
        self.assertEqual(len(quests), 1)
        quest_data = quests[0]
        self.assertEqual(quest_data['title'], 'Weekly Hustle: Apply to a Job')

        # Check HTML renders quest-toast
        page_res = self.client.get(reverse('jobs.index'))
        self.assertEqual(page_res.status_code, 200)
        self.assertContains(page_res, 'quest-toast')
        self.assertContains(page_res, 'Quest Completed!')

        # Mark quest viewed
        mark_res = self.client.get(reverse('leveling:api_mark_quest_viewed', kwargs={'user_quest_id': quest_data['id']}))
        self.assertEqual(mark_res.status_code, 200)
        self.assertTrue(mark_res.json()['success'])

        # API should now return 0 unviewed quests
        res_after = self.client.get(reverse('leveling:api_unviewed'))
        self.assertEqual(res_after.json().get('quests', []), [])

    def test_onboarding_signup_awards_locking_in_achievement(self):
        signup_res = self.client.post(reverse('accounts.signup'), {
            'username': 'newbie_sam',
            'email': 'sam@example.com',
            'password': 'password123',
            'role': 'job_seeker'
        })
        self.assertEqual(signup_res.status_code, 200)
        self.assertContains(signup_res, 'Locking In...')
        self.assertNotContains(signup_res, 'LEVEL UP!')
        self.assertContains(signup_res, reverse('accounts.edit_profile'))

        newbie = User.objects.get(username='newbie_sam')
        level_profile = UserLevelProfile.objects.get(user=newbie)
        self.assertEqual(level_profile.xp, 0)
        self.assertEqual(level_profile.level, 1)
        self.assertEqual(level_profile.rank_title, 'Job Seeker Novice')

    def test_first_profile_save_awards_locked_in_and_shows_quests_link(self):
        # Create user via signup
        self.client.post(reverse('accounts.signup'), {
            'username': 'designer_dave',
            'email': 'dave@example.com',
            'password': 'password123',
            'role': 'job_seeker'
        })
        dave = User.objects.get(username='designer_dave')

        # First save profile
        res = self.client.post(reverse('accounts.edit_profile'), {
            'first_name': 'Dave',
            'last_name': 'Miller',
            'headline': 'UI/UX Developer',
            'skills': 'Figma, CSS, Django'
        }, follow=True)
        self.assertRedirects(res, reverse('accounts.profile', kwargs={'username': 'designer_dave'}))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Locked In.')
        self.assertNotContains(res, '+150 XP Earned')
        self.assertContains(res, "You're Officially Locked In!")
        self.assertContains(res, reverse('leveling:dashboard') + '?tutorial=1')

        # Dave should have 0 XP and stay at Level 1 (Job Seeker Novice)
        level_profile = UserLevelProfile.objects.get(user=dave)
        self.assertEqual(level_profile.xp, 0)
        self.assertEqual(level_profile.level, 1)

        # Subsequent save does not trigger welcome again, redirects to profile
        res2 = self.client.post(reverse('accounts.edit_profile'), {
            'first_name': 'Dave',
            'last_name': 'Miller',
            'headline': 'Senior UI/UX Developer',
            'skills': 'Figma, CSS, Django, Python'
        })
        self.assertRedirects(res2, reverse('accounts.profile', kwargs={'username': 'designer_dave'}))

    def test_quests_dashboard_tutorial_rendered(self):
        self.client.login(username='applicant_bob', password='password123')

        # Without tutorial parameter: no tutorial card
        res_normal = self.client.get(reverse('leveling:dashboard'))
        self.assertEqual(res_normal.status_code, 200)
        self.assertNotContains(res_normal, 'Welcome to Your Gamified Job Hunt!')

        # With tutorial parameter: shows tutorial card
        res_tut = self.client.get(reverse('leveling:dashboard') + '?tutorial=1')
        self.assertEqual(res_tut.status_code, 200)
        self.assertContains(res_tut, 'Welcome to Your Gamified Job Hunt!')
        self.assertContains(res_tut, '1. XP & Levels')
        self.assertContains(res_tut, '2. Weekly Quests')
        self.assertContains(res_tut, '3. Achievements')
        self.assertContains(res_tut, reverse('jobs.index') + '?demo=1')

    def test_quests_locked_and_do_not_progress_during_onboarding(self):
        # Create fresh user
        user = User.objects.create_user(
            username='fresh_user',
            email='fresh@example.com',
            password='password123'
        )
        Profile.objects.create(user=user, role='job_seeker')
        level_profile = get_or_create_user_level_profile(user)
        self.assertFalse(level_profile.tutorial_completed)

        # Quests should be empty / locked
        quests = ensure_user_quests(user)
        self.assertEqual(quests.count(), 0)

        # Updating profile should NOT complete or progress "Polish the Resume" quest
        self.client.login(username='fresh_user', password='password123')
        self.client.post(reverse('accounts.edit_profile'), {
            'first_name': 'Fresh',
            'last_name': 'Candidate',
            'headline': 'Full Stack Developer',
            'skills': 'Python, React'
        })

        # Quests still 0
        self.assertEqual(UserQuest.objects.filter(user=user).count(), 0)

        # Dashboard shows locked state
        res = self.client.get(reverse('leveling:dashboard'))
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.context['quests_unlocked'])
        self.assertContains(res, 'Weekly Quests are Locked')
        self.assertContains(res, reverse('jobs.index') + '?demo=1')

    def test_complete_onboarding_tutorial_flow_with_google_demo(self):
        # 1. Sign up
        signup_res = self.client.post(reverse('accounts.signup'), {
            'username': 'alice_tutorial',
            'email': 'alice@example.com',
            'password': 'password123',
            'role': 'job_seeker'
        })
        alice = User.objects.get(username='alice_tutorial')
        profile = UserLevelProfile.objects.get(user=alice)
        self.assertFalse(profile.tutorial_completed)
        self.assertEqual(profile.level, 1) # Intro achievement has 0 XP
        self.assertEqual(profile.xp, 0)

        # 2. Complete Profile
        profile_res = self.client.post(reverse('accounts.edit_profile'), {
            'first_name': 'Alice',
            'last_name': 'Wonderland',
            'headline': 'Software Engineer in Training',
            'skills': 'Python, Django, Algorithms'
        }, follow=True)
        self.assertRedirects(profile_res, reverse('accounts.profile', kwargs={'username': 'alice_tutorial'}))
        self.assertContains(profile_res, reverse('leveling:dashboard') + '?tutorial=1')

        # Quests are not generated yet
        self.assertEqual(UserQuest.objects.filter(user=alice).count(), 0)
        profile.refresh_from_db()
        self.assertEqual(profile.xp, 0)
        self.assertEqual(profile.level, 1)

        # 3. Visit Quests Page (?tutorial=1)
        quest_page_res = self.client.get(reverse('leveling:dashboard') + '?tutorial=1')
        self.assertEqual(quest_page_res.status_code, 200)
        self.assertFalse(quest_page_res.context['quests_unlocked'])
        self.assertContains(quest_page_res, 'Welcome to Your Gamified Job Hunt!')
        self.assertContains(quest_page_res, reverse('jobs.index') + '?demo=1')

        # 4. Visit Job Discovery with ?demo=1
        discovery_res = self.client.get(reverse('jobs.index') + '?demo=1')
        self.assertEqual(discovery_res.status_code, 200)
        self.assertTrue(discovery_res.context['template_data']['demo_mode'])
        demo_job = discovery_res.context['template_data']['demo_job']
        self.assertIsNotNone(demo_job)
        self.assertEqual(demo_job.title, 'Software Engineer - Google (Demo)')
        self.assertContains(discovery_res, 'Software Engineer - Google (Demo)')
        self.assertContains(discovery_res, 'Tutorial Mission: First Application')

        # 5. Visit Demo Job Details
        demo_detail_res = self.client.get(reverse('jobs.detail', kwargs={'id': demo_job.id}) + '?demo=1')
        self.assertEqual(demo_detail_res.status_code, 200)
        self.assertTrue(demo_detail_res.context['is_demo_job'])
        self.assertContains(demo_detail_res, 'Interactive Tutorial: Inspecting & Applying to a Job')
        self.assertContains(demo_detail_res, 'Apply Now (Practice Demo)')

        # 6. Apply to Demo Job -> Awards "First Step" achievement (+50 XP)!
        apply_res = self.client.post(reverse('jobs.apply', kwargs={'id': demo_job.id}), {
            'cover_letter': 'Hello Google! I am applying as part of my tutorial.'
        })
        self.assertRedirects(apply_res, reverse('leveling:dashboard') + '?tutorial=conclude')

        # Verify "First Step" achievement was unlocked
        first_step = Achievement.objects.get(slug='first_step')
        ua = UserAchievement.objects.get(user=alice, achievement=first_step)
        self.assertTrue(ua.unlocked)

        # Alice now has 50 XP
        profile.refresh_from_db()
        self.assertEqual(profile.xp, 50)
        self.assertEqual(profile.level, 1)

        # Verify demo application didn't count towards real profile applications counter
        self.assertEqual(profile.total_applications, 0)

        # 7. Visit Quests Page with ?tutorial=conclude
        conclude_res = self.client.get(reverse('leveling:dashboard') + '?tutorial=conclude')
        self.assertEqual(conclude_res.status_code, 200)
        profile.refresh_from_db()
        self.assertTrue(profile.tutorial_completed)
        self.assertTrue(conclude_res.context['quests_unlocked'])
        self.assertContains(conclude_res, 'Tutorial Complete!')
        self.assertContains(conclude_res, 'First Step')
        self.assertContains(conclude_res, 'Weekly Quests are now Live!')

        # Weekly quests are now generated
        self.assertGreater(UserQuest.objects.filter(user=alice).count(), 0)

        # 8. Subsequent profile edit now progresses the "Polish the Resume" quest
        self.client.post(reverse('accounts.edit_profile'), {
            'first_name': 'Alice',
            'last_name': 'Wonderland',
            'headline': 'Senior Software Engineer',
            'skills': 'Python, Django, Algorithms, System Design'
        })

        resume_quest = Quest.objects.get(slug='weekly_update_profile')
        start_date, _ = get_current_week_boundaries()
        uq = UserQuest.objects.get(user=alice, quest=resume_quest, period_start=start_date)
        self.assertTrue(uq.is_completed)




