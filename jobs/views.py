from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.urls import reverse
from jobs.models import JobPosting, JobApplication, JobReport
from accounts.models import Profile


def get_or_create_demo_job():
    """Gets or creates the fake practice job for onboarding tutorial."""
    from django.contrib.auth.models import User
    demo_recruiter, _ = User.objects.get_or_create(
        username='google_recruiter_demo',
        defaults={
            'first_name': 'Google',
            'last_name': 'Recruiting Team',
            'email': 'recruiting-demo@google.com',
        }
    )
    if not hasattr(demo_recruiter, 'profile'):
        Profile.objects.get_or_create(
            user=demo_recruiter,
            defaults={'role': 'employer', 'headline': 'Google University & Early Career Recruiting'}
        )
    demo_job, _ = JobPosting.objects.get_or_create(
        title='Software Engineer - Google (Demo)',
        defaults={
            'description': (
                'Welcome to your first practice job application on LockedIn!\n\n'
                'Google is looking for curious, mission-driven software engineers to build products that impact billions.\n'
                'In this tutorial role, you will learn how easy it is to inspect job details, write or attach a cover letter, '
                'and submit your application.\n\n'
                '✨ Try clicking the "Apply Now" button below and submit this demo application to complete your tutorial and unlock weekly quests!'
            ),
            'recruiter': demo_recruiter,
            'work_type': 'hybrid',
            'required_skills': 'Python, JavaScript, Teamwork, Problem Solving',
            'location': 'Mountain View, CA (or Remote)',
            'salary_min': 120000,
            'salary_max': 165000,
            'visa_sponsorship': True,
            'status': 'active',
        }
    )
    return demo_job


def index(request):
    jobs = JobPosting.objects.filter(status='active').exclude(title__icontains='(Demo)').order_by('-date')

    demo_mode = request.GET.get('demo') == '1'
    demo_job = None
    demo_applied = False
    if demo_mode:
        demo_job = get_or_create_demo_job()
        if request.user.is_authenticated:
            demo_applied = request.user.job_applications.filter(job=demo_job).exists()

    if request.user.is_authenticated:
        try:
            if request.user.profile.role == 'job_seeker':
                applied_ids = request.user.job_applications.values_list('job_id', flat=True)
                jobs = jobs.exclude(id__in=applied_ids)
        except Exception:
            pass

    title = (request.GET.get('title') or '').strip()
    skills = (request.GET.get('skills') or '').strip()
    location = (request.GET.get('location') or '').strip()
    salary_min = request.GET.get('salary_min', '').strip()
    salary_max = request.GET.get('salary_max', '').strip()
    work_type = (request.GET.get('work_type') or '').strip()
    visa_sponsorship = request.GET.get('visa_sponsorship')

    if title:
        jobs = jobs.filter(title__icontains=title)
    if skills:
        jobs = jobs.filter(required_skills__icontains=skills)
    if location:
        jobs = jobs.filter(location__icontains=location)
    if salary_min:
        try:
            jobs = jobs.filter(salary_max__gte=int(salary_min))
        except ValueError:
            pass
    if salary_max:
        try:
            jobs = jobs.filter(salary_min__lte=int(salary_max))
        except ValueError:
            pass
    if work_type in ['in-person', 'hybrid', 'remote']:
        jobs = jobs.filter(work_type=work_type)
    if visa_sponsorship == 'on':
        jobs = jobs.filter(visa_sponsorship=True)

    template_data = {
        'title': 'Job Discovery | LockedIn',
        'jobs': jobs,
        'demo_mode': demo_mode,
        'demo_job': demo_job,
        'demo_applied': demo_applied,
        'filters': {
            'title': title,
            'skills': skills,
            'location': location,
            'salary_min': salary_min,
            'salary_max': salary_max,
            'work_type': work_type,
            'visa_sponsorship': visa_sponsorship,
        },
    }
    return render(request, 'jobs/index.html', context={'template_data': template_data})


@login_required
def for_you(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if profile.role != 'job_seeker':
        messages.error(request, 'This page is only for job seekers.')
        return redirect('home.index')

    user_skills = {
        skill.strip().lower()
        for skill in (profile.skills or '').replace(',', ' ').split()
        if skill.strip()
    }

    applied_ids = request.user.job_applications.values_list('job_id', flat=True)
    jobs = JobPosting.objects.filter(status='active').exclude(id__in=applied_ids).order_by('-date')
    recommended_jobs = []

    if user_skills:
        for job in jobs:
            job_skills = {
                skill.strip().lower()
                for skill in (job.required_skills or '').replace(',', ' ').split()
                if skill.strip()
            }
            if user_skills & job_skills:
                recommended_jobs.append(job)

    template_data = {
        'title': 'For You | LockedIn',
    }

    return render(request, 'jobs/for_you.html', {
        'template_data': template_data,
        'jobs': recommended_jobs,
        'has_profile_skills': bool(user_skills),
    })


def detail(request, id):
    job = get_object_or_404(JobPosting, id=id, status='active')
    template_data = {
        'title': f'{job.title} | LockedIn',
    }

    from_source = request.GET.get('from', '').strip()
    if not from_source:
        referer = request.META.get('HTTP_REFERER', '')
        if 'for-you' in referer:
            from_source = 'for_you'
        elif 'jobs' in referer:
            from_source = 'discovery'

    is_applied = request.user.is_authenticated and request.user.job_applications.filter(job=job).exists()
    is_demo_job = '(Demo)' in job.title or request.GET.get('demo') == '1'

    return render(request, 'jobs/detail.html', {
        'template_data': template_data,
        'job': job,
        'is_applied': is_applied,
        'is_demo_job': is_demo_job,
        'from_source': from_source,
        'report_reasons': JobReport.REASON_CHOICES,
    })


@login_required
def apply(request, id):
    job = get_object_or_404(JobPosting, id=id, status='active')
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if profile.role != 'job_seeker':
        messages.error(request, 'Only job seekers can apply to positions.')
        return redirect('jobs.detail', id=job.id)

    is_demo = '(Demo)' in job.title
    if is_demo:
        if JobApplication.objects.filter(job=job, applicant=request.user).exists():
            messages.info(request, 'You have already completed the demo practice application.')
            return redirect(reverse('leveling:dashboard') + '?tutorial=conclude')

        cover_letter = (request.POST.get('cover_letter', '') or '').strip()
        JobApplication.objects.create(
            job=job,
            applicant=request.user,
            cover_letter=cover_letter,
            status='applied',
        )
        messages.success(request, '🎉 Practice application submitted! You unlocked the "First Step" achievement (+50 XP).')
        return redirect(reverse('leveling:dashboard') + '?tutorial=conclude')

    from_source = (request.POST.get('from') or request.GET.get('from') or '').strip()
    if not from_source:
        referer = request.META.get('HTTP_REFERER', '')
        if 'for-you' in referer:
            from_source = 'for_you'
        else:
            from_source = 'discovery'

    redirect_target = 'jobs.for_you' if from_source == 'for_you' else 'jobs.index'

    if JobApplication.objects.filter(job=job, applicant=request.user).exists():
        messages.info(request, f'You have already applied to "{job.title}".')
        return redirect(redirect_target)

    cover_letter = (request.POST.get('cover_letter', '') or '').strip()

    JobApplication.objects.create(
        job=job,
        applicant=request.user,
        cover_letter=cover_letter,
        status='applied',
    )

    messages.success(request, f'Your application for "{job.title}" has been sent to the employer.')
    return redirect(redirect_target)


@login_required
def report_job(request, id):
    job = get_object_or_404(JobPosting, id=id)

    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        details = request.POST.get('details', '').strip()

        valid_reasons = dict(JobReport.REASON_CHOICES).keys()
        if reason not in valid_reasons:
            messages.error(request, 'Please select a valid report reason.')
            return redirect('jobs.detail', id=job.id)

        JobReport.objects.create(
            job=job,
            reporter=request.user,
            reason=reason,
            details=details,
            status='pending',
        )

        messages.success(request, 'Thank you for your report. It has been submitted to moderators for review.')

    return redirect('jobs.detail', id=job.id)



@login_required
def applications(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if profile.role != 'job_seeker':
        messages.error(request, 'This page is only for applicants.')
        return redirect('home.index')

    applications = JobApplication.objects.filter(
        applicant=request.user
    ).select_related('job', 'job__recruiter').order_by('-submitted_at')

    template_data = {
        'title': 'My Applications | LockedIn',
    }

    return render(request, 'jobs/applications.html', {
        'template_data': template_data,
        'applications': applications,
    })


@login_required
def applicants(request, id):
    job = get_object_or_404(JobPosting, id=id, recruiter=request.user)
    demo_mode = request.GET.get('demo') == '1' or request.POST.get('demo') == '1' or '(Demo)' in job.title

    if request.method == 'POST':
        application_id = request.POST.get('application_id')
        status = request.POST.get('status', '').strip()

        if application_id:
            application = get_object_or_404(job.applications, id=application_id)
            valid_statuses = ['applied', 'review', 'interview', 'offer', 'closed']

            if status in valid_statuses:
                application.status = status
                application.save()
                if status == 'closed':
                    messages.success(request, f'{application.applicant.username} was denied and marked as closed.')
                else:
                    messages.success(request, f'{application.applicant.username} status updated to {application.status_label}.')
            else:
                messages.error(request, 'Invalid application status.')

        if demo_mode:
            from leveling.services import award_first_step_achievement
            award_first_step_achievement(request.user)
            messages.success(request, '🎉 Practice applicant reviewed! You unlocked the "First Step" achievement (+50 XP).')
            return redirect(reverse('leveling:dashboard') + '?tutorial=conclude')

        return redirect('jobs.applicants', id=job.id)

    applications = job.applications.select_related('applicant').order_by('-submitted_at')
    template_data = {
        'title': f'Applicants for {job.title} | LockedIn',
    }

    return render(request, 'jobs/applicants.html', {
        'template_data': template_data,
        'job': job,
        'applications': applications,
        'demo_mode': demo_mode,
    })

@login_required
def create_job(request):
    demo_mode = request.GET.get('demo') == '1' or request.POST.get('demo') == '1'
    template_data = {
        "title": "Post a Practice Job | LockedIn" if demo_mode else "Post a Job | LockedIn"
    }

    is_employer = Profile.objects.filter(
        user=request.user,
        role='employer',
    ).exists()

    if not is_employer:
        messages.error(request, 'Only employers can post jobs.')
        return redirect('home.index')

    if request.method == 'POST':
        title = request.POST.get('title','').strip()
        description = request.POST.get('description','').strip()
        location = request.POST.get('location','').strip()
        work_type = request.POST.get('work_type','').strip()
        visa_sponsorship = 'visa_sponsorship' in request.POST
        required_skills = request.POST.get('required_skills', '').strip()
        try:
            salary_min = int(request.POST.get('salary_min',''))
            salary_max = int(request.POST.get('salary_max',''))
        except ValueError:
            messages.error(request, 'Salaries must be valid whole numbers')
            return render(
                request,
                'jobs/job_form.html',
                context={"template_data": template_data, "demo_mode": demo_mode}
            )
        if not all([title, description, location, required_skills, work_type]):
            messages.error(request, 'All fields must be completed')
            return render(
                request,
                'jobs/job_form.html',
                context={"template_data": template_data, "demo_mode": demo_mode}
            )
        if not work_type in ["in-person", "hybrid", "remote"]:
            messages.error(request, 'Work type must be in-person, hybrid, or remote')
            return render(
                request,
                'jobs/job_form.html',
                context={"template_data": template_data, "demo_mode": demo_mode}
            )
        if salary_min > 99999999 or salary_max > 99999999:
            messages.error(request, 'Salaries must not exceed limit')
            return render(
                request,
                'jobs/job_form.html',
                context={"template_data": template_data, "demo_mode": demo_mode}
            )
        if salary_min < 0 or salary_max < 0:
            messages.error(request, 'Salaries cannot be negative')
            return render(
                request,
                'jobs/job_form.html',
                context={"template_data": template_data, "demo_mode": demo_mode}
            )
        if salary_min > salary_max:
            messages.error(request, 'Minimum salary cannot be greater than the maximum salary')
            return render(
                request,
                'jobs/job_form.html',
                context={"template_data": template_data, "demo_mode": demo_mode}
            )

        if demo_mode and '(Demo)' not in title:
            title = f"{title} (Demo)"

        job = JobPosting()
        job.title = title
        job.description = description
        job.location = location
        job.work_type = work_type
        job.required_skills = required_skills
        job.salary_min = salary_min
        job.salary_max = salary_max
        job.visa_sponsorship = visa_sponsorship
        job.recruiter = request.user
        job.save()

        if demo_mode:
            # Create or retrieve fake demo applicant Alex Morgan
            demo_user, _ = User.objects.get_or_create(
                username='alex_candidate_demo',
                defaults={
                    'first_name': 'Alex',
                    'last_name': 'Morgan',
                    'email': 'alex.morgan.demo@example.com',
                }
            )
            Profile.objects.get_or_create(
                user=demo_user,
                defaults={
                    'role': 'job_seeker',
                    'headline': 'Full Stack Developer | Python, Django, React',
                    'about': 'Passionate software developer with experience building responsive web applications. Enthusiastic about joining an innovative and collaborative engineering team.',
                    'skills': 'Python, Django, JavaScript, React, PostgreSQL, Docker, Git',
                    'education': 'B.S. in Computer Science',
                    'city': 'San Francisco',
                    'state': 'California',
                    'country': 'United States',
                    'is_private': False,
                }
            )
            JobApplication.objects.create(
                job=job,
                applicant=demo_user,
                cover_letter="Hello Hiring Team!\n\nI am thrilled to submit my application for this role. With my background in Python and full-stack development, I am confident I can make an immediate positive impact on your projects. Thank you for your time and consideration!",
                status='applied',
            )
            messages.success(
                request,
                '🎉 Practice job created! A sample candidate (Alex Morgan) has just applied. Now review their application to complete your training!'
            )
            return redirect(reverse('jobs.applicants', kwargs={'id': job.id}) + '?demo=1')

        messages.success(
            request,
            'Job posting created successfully.',
        )
        return redirect('jobs.my_jobs')

    demo_job = None
    if demo_mode:
        demo_job = {
            'title': 'Software Engineer (Demo)',
            'description': 'We are seeking a talented and motivated Software Engineer to join our engineering team. You will build and maintain modern web applications, collaborate with designers and product managers, and write clean, scalable code.',
            'location': 'Atlanta, GA (Hybrid)',
            'work_type': 'hybrid',
            'required_skills': 'Python, Django, JavaScript, SQL, Git',
            'salary_min': 85000,
            'salary_max': 125000,
            'visa_sponsorship': True,
        }

    return render(
        request,
        'jobs/job_form.html',
        context={
            "template_data": template_data,
            "demo_mode": demo_mode,
            "job": demo_job,
        }
    )


@login_required
def my_jobs(request):
    is_employer = Profile.objects.filter(
        user=request.user,
        role='employer',
    ).exists()

    if not is_employer:
        messages.error(request, 'Only employers can post jobs.')
        return redirect('home.index')

    jobs = JobPosting.objects.filter(
        recruiter=request.user
    ).order_by('-date')

    template_data = {
        "title" : "My Postings | LockedIn",
        "jobs" : jobs
    }

    return render(request, "jobs/my_jobs.html", context={"template_data" : template_data})


@login_required
def edit_job(request, id):
    is_employer = Profile.objects.filter(
        user=request.user,
        role='employer',
    ).exists()

    if not is_employer:
        messages.error(request, 'Only employers can post jobs.')
        return redirect('home.index')

    job = get_object_or_404(
        JobPosting,
        id=id,
        recruiter=request.user,
    )

    if job.status == 'removed':
        messages.error(
            request,
            'A removed job posting cannot be edited.',
        )
        return redirect('jobs.my_jobs')

    template_data = {
        "title" : "Edit Job | LockedIn"
    }

    if request.method == 'POST':
        title = request.POST.get('title','').strip()
        description = request.POST.get('description','').strip()
        location = request.POST.get('location','').strip()
        work_type = request.POST.get('work_type','').strip()
        visa_sponsorship = 'visa_sponsorship' in request.POST
        required_skills = request.POST.get('required_skills', '').strip()
        status = request.POST.get('status', '').strip()
        try:
            salary_min = int(request.POST.get('salary_min',''))
            salary_max = int(request.POST.get('salary_max',''))
        except ValueError:
            messages.error(request, 'Salaries must be valid whole numbers')
            return render(
                request,
                'jobs/job_form.html',
                context={"template_data" : template_data, "job" : job}
            )

        if status not in ["active", "closed"]:
            messages.error(request, 'Status must be active or closed')
            return render(
                request,
                'jobs/job_form.html',
                context={"template_data" : template_data, "job" : job}
            )

        if not all([title, description, location, required_skills, work_type]):
            messages.error(request, 'All fields must be completed')
            return render(
                request,
                'jobs/job_form.html',
                context={"template_data" : template_data, "job" : job}
            )
        if not work_type in ["in-person", "hybrid", "remote"]:
            messages.error(request, 'Work type must be in-person, hybrid, or remote')
            return render(
                request,
                'jobs/job_form.html',
                context={"template_data" : template_data, "job" : job}
            )
        if salary_min > 99999999 or salary_max > 99999999:
            messages.error(request, 'Salaries must not exceed limit')
            return render(
                request,
                'jobs/job_form.html',
                context={"template_data" : template_data, "job" : job}
            )
        if salary_min < 0 or salary_max < 0:
            messages.error(request, 'Salaries cannot be negative')
            return render(
                request,
                'jobs/job_form.html',
                context={"template_data" : template_data, "job" : job}
            )
        if salary_min > salary_max:
            messages.error(request, 'Minimum salary cannot be greater than the maximum salary')
            return render(
                request,
                'jobs/job_form.html',
                context={"template_data" : template_data, "job" : job}
            )

        job.title = title
        job.description = description
        job.location = location
        job.work_type = work_type
        job.required_skills = required_skills
        job.salary_min = salary_min
        job.salary_max = salary_max
        job.visa_sponsorship = visa_sponsorship
        job.status = status
        job.save()

        messages.success(
            request,
            'Job posting edited successfully.',
        )
        return redirect('jobs.my_jobs')



    return render(request, 'jobs/job_form.html', context={
        "template_data" : template_data,
        'job' : job
        })