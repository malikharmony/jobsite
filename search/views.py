from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from accounts.models import Profile


def index(request):
    return render(request, 'search/index.html')

@login_required
def candidates(request):
    is_employer = Profile.objects.filter(
        user=request.user,
        role='employer',
    ).exists()

    if not is_employer:
        messages.error(
            request,
            'Only employers can search for candidates.',
        )
        return redirect('home.index')


    skills = request.GET.get('skills', '').strip()
    location = request.GET.get('location', '').strip()
    projects = request.GET.get('projects', '').strip()

    candidate_profiles = Profile.objects.filter(
        role='job_seeker',
        user__is_active=True,
    )

    if not (request.user.is_staff or request.user.is_superuser):
        candidate_profiles = candidate_profiles.filter(is_private=False)

    if skills:
        candidate_profiles = candidate_profiles.filter(
            skills__icontains=skills
        )

    if location:
        candidate_profiles = candidate_profiles.filter(
            location__icontains=location
        )

    if projects:
        candidate_profiles = candidate_profiles.filter(
            projects__icontains=projects
        )

    template_data = {
        'title': 'Find Candidates | LockedIn',
        'candidates': candidate_profiles,
        'skills': skills,
        'location': location,
        'projects': projects,
    }

    return render(
        request, 'search/candidate_search.html', {"template_data" : template_data}
    )