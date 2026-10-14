from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import Profile

class ProfilePrivacyTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.seeker = User.objects.create_user(
            username='seeker1',
            email='seeker1@example.com',
            password='password123',
            first_name='Jane',
            last_name='Doe'
        )
        self.seeker_profile, _ = Profile.objects.get_or_create(
            user=self.seeker,
            role='job_seeker',
            headline='Software Engineer',
            location='Atlanta, GA',
            about='Passionate builder',
            education='Georgia Tech',
            experience='Tech Corp Intern',
            skills='Python, Django',
            projects='Job Portal Project',
            is_private=False
        )

        self.recruiter = User.objects.create_user(
            username='recruiter1',
            email='recruiter1@example.com',
            password='password123',
            first_name='Bob',
            last_name='Recruiter'
        )
        Profile.objects.get_or_create(user=self.recruiter, role='employer')

        self.admin = User.objects.create_user(
            username='admin1',
            email='admin1@example.com',
            password='password123',
            is_staff=True,
            is_superuser=True
        )
        Profile.objects.get_or_create(user=self.admin, role='employer')

    def test_save_privacy_settings(self):
        self.client.login(username='seeker1', password='password123')
        post_data = {
            'first_name': 'Jane',
            'last_name': 'Doe',
            'username': 'seeker1',
            'headline': 'Updated Headline',
            'about': 'Updated About',
            'education': 'Georgia Tech',
            'experience': 'Tech Corp Intern',
            'skills': 'Python, Django',
            'city': 'Atlanta',
            'state': 'GA',
            'country': 'USA',
            'projects': 'Job Portal Project',
            'is_private': 'on',
            'show_skills': 'on',
        }
        response = self.client.post('/accounts/profile/edit/', post_data)
        self.assertEqual(response.status_code, 302)

        self.seeker_profile.refresh_from_db()
        self.assertTrue(self.seeker_profile.is_private)
        self.assertTrue(self.seeker_profile.show_skills)
        self.assertFalse(self.seeker_profile.show_email)
        self.assertFalse(self.seeker_profile.show_location)
        self.assertFalse(self.seeker_profile.show_education)
        self.assertFalse(self.seeker_profile.show_experience)
        self.assertFalse(self.seeker_profile.show_projects)
        self.assertEqual(self.seeker_profile.city, 'Atlanta')
        self.assertEqual(self.seeker_profile.state, 'GA')
        self.assertEqual(self.seeker_profile.country, 'USA')
        self.assertEqual(self.seeker_profile.location, 'Atlanta, GA, USA')

    def test_private_profile_hidden_from_public(self):
        self.seeker_profile.is_private = True
        self.seeker_profile.save()

        response = self.client.get(f'/{self.seeker.username}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This profile is private.')
        self.assertNotContains(response, 'Passionate builder')
        self.assertNotContains(response, 'adminPrivateNoticeModal')

    def test_private_profile_hidden_from_recruiter(self):
        self.seeker_profile.is_private = True
        self.seeker_profile.save()

        self.client.login(username='recruiter1', password='password123')
        response = self.client.get(f'/{self.seeker.username}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This profile is private.')
        self.assertNotContains(response, 'Passionate builder')
        self.assertNotContains(response, 'adminPrivateNoticeModal')

    def test_private_profile_visible_to_owner(self):
        self.seeker_profile.is_private = True
        self.seeker_profile.save()

        self.client.login(username='seeker1', password='password123')
        response = self.client.get(f'/{self.seeker.username}/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'This profile is private.')
        self.assertContains(response, 'Passionate builder')
        self.assertContains(response, 'Edit Profile')
        self.assertNotContains(response, 'adminPrivateNoticeModal')

    def test_private_profile_visible_to_admin_with_modal(self):
        self.seeker_profile.is_private = True
        self.seeker_profile.save()

        self.client.login(username='admin1', password='password123')
        response = self.client.get(f'/{self.seeker.username}/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'This profile is private.')
        self.assertContains(response, 'Passionate builder')
        self.assertContains(response, 'adminPrivateNoticeModal')
        self.assertContains(response, 'Admin Notice')
        self.assertContains(response, 'triggerAdminPrivateNotice')

    def test_public_profile_admin_no_modal(self):
        self.seeker_profile.is_private = False
        self.seeker_profile.save()

        self.client.login(username='admin1', password='password123')
        response = self.client.get(f'/{self.seeker.username}/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'adminPrivateNoticeModal')

    def test_granular_section_privacy(self):
        self.seeker_profile.is_private = False
        self.seeker_profile.show_education = True
        self.seeker_profile.show_email = False
        self.seeker_profile.save()

        self.client.login(username='recruiter1', password='password123')
        response = self.client.get(f'/{self.seeker.username}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Passionate builder')
        self.assertNotContains(response, 'seeker1@example.com')
        self.assertContains(response, 'Georgia Tech')

        self.client.login(username='seeker1', password='password123')
        response = self.client.get(f'/{self.seeker.username}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Passionate builder')
        self.assertContains(response, 'Hidden from recruiters')

    def test_skip_for_now_and_cancel_buttons(self):
        self.client.login(username='seeker1', password='password123')
        response_existing = self.client.get('/accounts/profile/edit/')
        self.assertEqual(response_existing.status_code, 200)
        self.assertNotContains(response_existing, 'Skip for Now')
        self.assertContains(response_existing, f'href="/{self.seeker.username}/" class="btn btn-outline-secondary">Cancel</a>')

        response_new = self.client.get('/accounts/profile/edit/?new=1')
        self.assertEqual(response_new.status_code, 200)
        self.assertContains(response_new, 'Skip for Now')
        self.assertNotContains(response_new, f'href="/{self.seeker.username}/" class="btn btn-outline-secondary">Cancel</a>')

    def test_country_dropdown_and_state_dropdown_for_us(self):
        self.client.login(username='seeker1', password='password123')
        get_response = self.client.get('/accounts/profile/edit/')
        self.assertEqual(get_response.status_code, 200)
        self.assertContains(get_response, '<select class="form-select" id="country" name="country"')
        self.assertContains(get_response, '<select class="form-select" id="state" name="state"')
        self.assertContains(get_response, 'value="United States"')
        self.assertContains(get_response, 'value="Canada"')
        self.assertContains(get_response, 'value="Georgia"')

        post_data_canada = {
            'first_name': 'Jane',
            'last_name': 'Doe',
            'username': 'seeker1',
            'headline': 'Developer',
            'about': 'About me',
            'city': 'Toronto',
            'state': 'Ontario',
            'country': 'Canada',
        }
        res_canada = self.client.post('/accounts/profile/edit/', post_data_canada)
        self.assertEqual(res_canada.status_code, 302)
        self.seeker_profile.refresh_from_db()
        self.assertEqual(self.seeker_profile.country, 'Canada')
        self.assertEqual(self.seeker_profile.state, '')
        self.assertEqual(self.seeker_profile.location, 'Toronto, Canada')

        edit_canada = self.client.get('/accounts/profile/edit/')
        self.assertContains(edit_canada, 'id="state-col"')
        self.assertContains(edit_canada, 'd-none')

        post_data_us = {
            'first_name': 'Jane',
            'last_name': 'Doe',
            'username': 'seeker1',
            'headline': 'Developer',
            'about': 'About me',
            'city': 'Atlanta',
            'state': 'Georgia',
            'country': 'United States',
        }
        res_us = self.client.post('/accounts/profile/edit/', post_data_us)
        self.assertEqual(res_us.status_code, 302)
        self.seeker_profile.refresh_from_db()
        self.assertEqual(self.seeker_profile.country, 'United States')
        self.assertEqual(self.seeker_profile.state, 'Georgia')
        self.assertEqual(self.seeker_profile.location, 'Atlanta, Georgia, United States')

    def test_profile_photo_upload_and_removal(self):
        self.client.login(username='seeker1', password='password123')
        tiny_gif = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        uploaded_photo = SimpleUploadedFile('avatar.gif', tiny_gif, content_type='image/gif')

        post_data = {
            'first_name': 'Jane',
            'last_name': 'Doe',
            'username': 'seeker1',
            'headline': 'Developer',
            'about': 'About me',
            'city': 'Atlanta',
            'state': 'GA',
            'country': 'United States',
            'photo': uploaded_photo,
        }
        response = self.client.post('/accounts/profile/edit/', post_data)
        self.assertEqual(response.status_code, 302)

        self.seeker_profile.refresh_from_db()
        self.assertTrue(bool(self.seeker_profile.photo))

        profile_response = self.client.get(f'/{self.seeker.username}/')
        self.assertEqual(profile_response.status_code, 200)
        self.assertContains(profile_response, self.seeker_profile.photo.url)

        remove_response = self.client.post('/accounts/profile/edit/', {
            'first_name': 'Jane',
            'last_name': 'Doe',
            'username': 'seeker1',
            'headline': 'Developer',
            'about': 'About me',
            'city': 'Atlanta',
            'state': 'GA',
            'country': 'United States',
            'remove_photo': 'on',
        })
        self.assertEqual(remove_response.status_code, 302)
        self.seeker_profile.refresh_from_db()
        self.assertFalse(bool(self.seeker_profile.photo))


class ProfileCategoryTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='johndoe',
            email='johndoe@example.com',
            password='password123',
            first_name='John',
            last_name='Doe'
        )
        self.profile, _ = Profile.objects.get_or_create(
            user=self.user,
            role='job_seeker',
            location='San Francisco, CA',
            about='Experienced software engineer.'
        )

    def test_add_and_delete_education(self):
        self.client.login(username='johndoe', password='password123')
        post_data = {
            'school': 'MIT',
            'degree': 'Bachelor of Science',
            'major': 'Computer Science',
            'gpa': '3.9',
            'start_date': '2020-08-15',
            'end_date': '2024-05-15',
            'description': 'Dean list all semesters.',
        }
        response = self.client.post('/accounts/profile/education/add/', post_data)
        self.assertEqual(response.status_code, 302)

        self.assertEqual(self.profile.educations.count(), 1)
        edu = self.profile.educations.first()
        self.assertEqual(edu.school, 'MIT')
        self.assertEqual(edu.major, 'Computer Science')
        self.assertEqual(edu.gpa, '3.9')
        self.assertIn('Aug 2020 - May 2024', edu.enrollment_period)

        edit_data = {
            'school': 'Massachusetts Institute of Technology',
            'degree': 'Bachelor of Science',
            'major': 'Computer Science & AI',
            'gpa': '4.0',
            'start_date': '2020-08-15',
            'end_date': '2024-05-15',
            'description': 'Updated description.',
        }
        edit_response = self.client.post(f'/accounts/profile/education/{edu.id}/edit/', edit_data)
        self.assertEqual(edit_response.status_code, 302)
        edu.refresh_from_db()
        self.assertEqual(edu.school, 'Massachusetts Institute of Technology')
        self.assertEqual(edu.major, 'Computer Science & AI')
        self.assertEqual(edu.gpa, '4.0')

        del_response = self.client.post(f'/accounts/profile/education/{edu.id}/delete/')
        self.assertEqual(del_response.status_code, 302)
        self.assertEqual(self.profile.educations.count(), 0)

    def test_education_presently_enrolled(self):
        self.client.login(username='johndoe', password='password123')
        post_data = {
            'school': 'Stanford',
            'degree': 'MS',
            'major': 'Robotics',
            'start_date': '2024-09-01',
            'is_current': 'on',
        }
        response = self.client.post('/accounts/profile/education/add/', post_data)
        self.assertEqual(response.status_code, 302)
        edu = self.profile.educations.first()
        self.assertTrue(edu.is_current)
        self.assertIsNone(edu.end_date)
        self.assertIn('Sep 2024 - Present', edu.enrollment_period)

    def test_add_edit_and_delete_experience(self):
        self.client.login(username='johndoe', password='password123')
        post_data = {
            'title': 'Frontend Engineer',
            'company': 'Acme Corp',
            'location': 'New York, NY',
            'start_date': '2023-01-10',
            'is_current': 'on',
            'description': 'Building responsive web interfaces.',
        }
        response = self.client.post('/accounts/profile/experience/add/', post_data)
        self.assertEqual(response.status_code, 302)

        self.assertEqual(self.profile.experiences.count(), 1)
        exp = self.profile.experiences.first()
        self.assertEqual(exp.title, 'Frontend Engineer')
        self.assertEqual(exp.company, 'Acme Corp')
        self.assertTrue(exp.is_current)
        self.assertIn('Jan 2023 - Present', exp.period)

        edit_data = {
            'title': 'Senior Frontend Engineer',
            'company': 'Acme Global Corp',
            'location': 'Remote',
            'start_date': '2023-01-10',
            'is_current': 'on',
            'description': 'Leading UI development.',
        }
        edit_response = self.client.post(f'/accounts/profile/experience/{exp.id}/edit/', edit_data)
        self.assertEqual(edit_response.status_code, 302)
        exp.refresh_from_db()
        self.assertEqual(exp.title, 'Senior Frontend Engineer')
        self.assertEqual(exp.company, 'Acme Global Corp')

        del_response = self.client.post(f'/accounts/profile/experience/{exp.id}/delete/')
        self.assertEqual(del_response.status_code, 302)
        self.assertEqual(self.profile.experiences.count(), 0)

    def test_add_edit_and_delete_skill(self):
        self.client.login(username='johndoe', password='password123')
        response1 = self.client.post('/accounts/profile/skill/add/', {'name': 'Python', 'proficiency': 'Beginner'})
        self.assertEqual(response1.status_code, 302)

        skill = self.profile.skills_list.first()
        self.assertEqual(skill.name, 'Python')
        self.assertEqual(skill.proficiency, 'Beginner')

        edit_response = self.client.post(f'/accounts/profile/skill/{skill.id}/edit/', {'name': 'Python 3', 'proficiency': 'Expert'})
        self.assertEqual(edit_response.status_code, 302)
        skill.refresh_from_db()
        self.assertEqual(skill.name, 'Python 3')
        self.assertEqual(skill.proficiency, 'Expert')

        del_response = self.client.post(f'/accounts/profile/skill/{skill.id}/delete/')
        self.assertEqual(del_response.status_code, 302)
        self.assertEqual(self.profile.skills_list.count(), 0)

    def test_add_edit_and_delete_project(self):
        self.client.login(username='johndoe', password='password123')
        post_data = {
            'title': 'Portfolio Site',
            'technologies': 'Django, HTML, CSS',
            'link': 'https://example.com/portfolio',
            'description': 'My personal portfolio showcase.',
        }
        response = self.client.post('/accounts/profile/project/add/', post_data)
        self.assertEqual(response.status_code, 302)

        proj = self.profile.projects_list.first()
        self.assertEqual(proj.title, 'Portfolio Site')

        edit_data = {
            'title': 'Awesome Portfolio Site',
            'technologies': 'Django, React, PostgreSQL',
            'link': 'https://example.com/awesome',
            'description': 'Upgraded personal portfolio showcase.',
        }
        edit_response = self.client.post(f'/accounts/profile/project/{proj.id}/edit/', edit_data)
        self.assertEqual(edit_response.status_code, 302)
        proj.refresh_from_db()
        self.assertEqual(proj.title, 'Awesome Portfolio Site')
        self.assertEqual(proj.technologies, 'Django, React, PostgreSQL')

        del_response = self.client.post(f'/accounts/profile/project/{proj.id}/delete/')
        self.assertEqual(del_response.status_code, 302)
        self.assertEqual(self.profile.projects_list.count(), 0)

    def test_profile_sidebar_location_and_navigation(self):
        self.client.login(username='johndoe', password='password123')
        response = self.client.get(f'/{self.user.username}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'San Francisco, CA')
        self.assertContains(response, 'Experienced software engineer.')
        self.assertContains(response, '/accounts/profile/edit/#education-section')
        self.assertContains(response, '/accounts/profile/edit/#experience-section')
        self.assertContains(response, '/accounts/profile/edit/#skills-section')
        self.assertContains(response, '/accounts/profile/edit/#projects-section')
        self.assertNotContains(response, 'onclick="return confirm(\'Delete')


