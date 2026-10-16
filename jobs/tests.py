from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from accounts.models import Profile
from jobs.models import JobPosting, JobApplication, JobReport


class JobApplicationAndReportTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.recruiter = User.objects.create_user(
            username='recruiter_alice',
            email='alice@example.com',
            password='password123'
        )
        Profile.objects.create(user=self.recruiter, role='employer')

        self.job_seeker = User.objects.create_user(
            username='seeker_dan',
            email='dan@example.com',
            password='password123'
        )
        self.profile = Profile.objects.create(
            user=self.job_seeker,
            role='job_seeker',
            skills='Python, Django'
        )

        self.job1 = JobPosting.objects.create(
            title='Backend Engineer',
            description='Django backend developer needed',
            recruiter=self.recruiter,
            work_type='remote',
            required_skills='Python, Django',
            location='Atlanta, GA',
            salary_min=90000,
            salary_max=120000,
            status='active'
        )

        self.job2 = JobPosting.objects.create(
            title='Frontend Engineer',
            description='React and CSS specialist',
            recruiter=self.recruiter,
            work_type='hybrid',
            required_skills='JavaScript, React',
            location='New York, NY',
            salary_min=85000,
            salary_max=115000,
            status='active'
        )

    def test_apply_redirects_to_discovery_and_for_you_appropriately(self):
        self.client.login(username='seeker_dan', password='password123')

        # Apply from discovery
        res = self.client.post(
            reverse('jobs.apply', kwargs={'id': self.job1.id}),
            {'cover_letter': 'Hello', 'from': 'discovery'}
        )
        self.assertRedirects(res, reverse('jobs.index'))

        # Apply from for_you
        res2 = self.client.post(
            reverse('jobs.apply', kwargs={'id': self.job2.id}),
            {'cover_letter': 'Hello again', 'from': 'for_you'}
        )
        self.assertRedirects(res2, reverse('jobs.for_you'))

    def test_already_applied_job_is_hidden_from_listings(self):
        self.client.login(username='seeker_dan', password='password123')

        # Before applying, job1 is in discovery
        res_before = self.client.get(reverse('jobs.index'))
        self.assertContains(res_before, 'Backend Engineer')

        # Apply to job1
        JobApplication.objects.create(job=self.job1, applicant=self.job_seeker)

        # After applying, job1 is hidden from discovery
        res_after_discovery = self.client.get(reverse('jobs.index'))
        self.assertNotContains(res_after_discovery, 'Backend Engineer')
        self.assertContains(res_after_discovery, 'Frontend Engineer')

        # And hidden from for_you
        res_after_for_you = self.client.get(reverse('jobs.for_you'))
        self.assertNotContains(res_after_for_you, 'Backend Engineer')

    def test_cannot_reapply_to_same_job(self):
        self.client.login(username='seeker_dan', password='password123')

        # First apply
        JobApplication.objects.create(job=self.job1, applicant=self.job_seeker)
        self.assertEqual(JobApplication.objects.filter(job=self.job1, applicant=self.job_seeker).count(), 1)

        # Try to apply again
        res = self.client.post(
            reverse('jobs.apply', kwargs={'id': self.job1.id}),
            {'cover_letter': 'Trying again', 'from': 'discovery'}
        )
        self.assertRedirects(res, reverse('jobs.index'))
        # Count should still be 1
        self.assertEqual(JobApplication.objects.filter(job=self.job1, applicant=self.job_seeker).count(), 1)

    def test_detail_view_shows_applied_badge_and_report_button(self):
        self.client.login(username='seeker_dan', password='password123')

        # Detail view before apply shows Apply Now and Report
        res = self.client.get(reverse('jobs.detail', kwargs={'id': self.job1.id}))
        self.assertContains(res, 'Apply Now')
        self.assertContains(res, 'Report')

        # Apply
        JobApplication.objects.create(job=self.job1, applicant=self.job_seeker)

        # Detail view after apply shows Applied badge
        res_after = self.client.get(reverse('jobs.detail', kwargs={'id': self.job1.id}))
        self.assertContains(res_after, 'Applied')
        self.assertNotContains(res_after, 'Apply Now')
        self.assertContains(res_after, 'Report')

    def test_report_job_submission(self):
        self.client.login(username='seeker_dan', password='password123')

        res = self.client.post(
            reverse('jobs.report', kwargs={'id': self.job1.id}),
            {'reason': 'spam', 'details': 'Looks like a fake job posting'}
        )
        self.assertRedirects(res, reverse('jobs.detail', kwargs={'id': self.job1.id}))

        report = JobReport.objects.filter(job=self.job1, reporter=self.job_seeker).first()
        self.assertIsNotNone(report)
        self.assertEqual(report.reason, 'spam')
        self.assertEqual(report.details, 'Looks like a fake job posting')
        self.assertEqual(report.status, 'pending')
