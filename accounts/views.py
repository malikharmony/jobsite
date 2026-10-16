from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Profile, Education, Experience, Skill, Project

def index(request):
    if request.user.is_authenticated:
        return redirect('accounts.profile', username=request.user.username)
    return redirect('accounts.login')

def signup(request):
    if request.user.is_authenticated:
        return redirect('accounts.profile', username=request.user.username)

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        role = request.POST.get('role', 'job_seeker')

        if not username or not email or not password:
            messages.error(request, 'Please fill in all required fields.')
            template_data = {'title': 'Sign Up | LockedIn'}
            return render(request, 'accounts/signup.html', {'template_data': template_data})

        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, f'Username "{username}" is already taken. Please choose another.')
            template_data = {'title': 'Sign Up | LockedIn'}
            return render(request, 'accounts/signup.html', {'template_data': template_data})

        if User.objects.filter(email__iexact=email).exists():
            messages.error(request, 'An account with this email already exists.')
            template_data = {'title': 'Sign Up | LockedIn'}
            return render(request, 'accounts/signup.html', {'template_data': template_data})

        user = User.objects.create_user(username=username, email=email, password=password)
        Profile.objects.create(user=user, role=role)
        login(request, user)
        request.session['is_new_account'] = True

        from leveling.services import award_account_created_achievement
        ach, level_profile, leveled_up = award_account_created_achievement(user)

        template_data = {'title': 'Locking In... | LockedIn'}
        return render(request, 'accounts/signup_welcome.html', {
            'template_data': template_data,
            'achievement': ach,
            'level_profile': level_profile,
            'leveled_up': leveled_up,
            'continue_url': reverse('accounts.edit_profile'),
        })

    template_data = {'title': 'Sign Up | LockedIn'}
    return render(request, 'accounts/signup.html', {'template_data': template_data})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('accounts.profile', username=request.user.username)

    if request.method == 'POST':
        identifier = (
            request.POST.get('login_identifier', '').strip()
            or request.POST.get('email', '').strip()
            or request.POST.get('username', '').strip()
        )
        password = request.POST.get('password', '')

        user_obj = User.objects.filter(username__iexact=identifier).first()
        if not user_obj:
            user_obj = User.objects.filter(email__iexact=identifier).first()

        if user_obj:
            authenticated_user = authenticate(request, username=user_obj.username, password=password)
            if authenticated_user is not None:
                login(request, authenticated_user)

                profile, _ = Profile.objects.get_or_create(user=authenticated_user)
                if profile.headline or authenticated_user.first_name:
                    return redirect('accounts.profile', username=authenticated_user.username)
                
                return redirect('accounts.edit_profile')

        messages.error(request, 'Invalid username/email or password.')

    template_data = {'title': 'Sign In | LockedIn'}
    return render(request, 'accounts/login.html', {'template_data': template_data})

def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home.index')

COUNTRIES = [
    "United States", "Canada", "United Kingdom", "Australia", "Afghanistan", "Albania", "Algeria",
    "Andorra", "Angola", "Antigua and Barbuda", "Argentina", "Armenia", "Austria", "Azerbaijan",
    "Bahamas", "Bahrain", "Bangladesh", "Barbados", "Belarus", "Belgium", "Belize", "Benin",
    "Bhutan", "Bolivia", "Bosnia and Herzegovina", "Botswana", "Brazil", "Brunei", "Bulgaria",
    "Burkina Faso", "Burundi", "Cabo Verde", "Cambodia", "Cameroon", "Central African Republic",
    "Chad", "Chile", "China", "Colombia", "Comoros", "Congo", "Costa Rica", "Croatia", "Cuba",
    "Cyprus", "Czech Republic", "Denmark", "Djibouti", "Dominica", "Dominican Republic",
    "Ecuador", "Egypt", "El Salvador", "Equatorial Guinea", "Eritrea", "Estonia", "Eswatini",
    "Ethiopia", "Fiji", "Finland", "France", "Gabon", "Gambia", "Georgia", "Germany", "Ghana",
    "Greece", "Grenada", "Guatemala", "Guinea", "Guyana", "Haiti", "Honduras", "Hungary",
    "Iceland", "India", "Indonesia", "Iran", "Iraq", "Ireland", "Israel", "Italy", "Jamaica",
    "Japan", "Jordan", "Kazakhstan", "Kenya", "Kuwait", "Kyrgyzstan", "Laos", "Latvia", "Lebanon",
    "Liberia", "Libya", "Liechtenstein", "Lithuania", "Luxembourg", "Madagascar", "Malawi",
    "Malaysia", "Maldives", "Mali", "Malta", "Mexico", "Moldova", "Monaco", "Mongolia",
    "Montenegro", "Morocco", "Mozambique", "Myanmar", "Namibia", "Nepal", "Netherlands",
    "New Zealand", "Nicaragua", "Niger", "Nigeria", "North Korea", "North Macedonia", "Norway",
    "Oman", "Pakistan", "Palestine", "Panama", "Papua New Guinea", "Paraguay", "Peru",
    "Philippines", "Poland", "Portugal", "Qatar", "Romania", "Russia", "Rwanda", "Saudi Arabia",
    "Senegal", "Serbia", "Singapore", "Slovakia", "Slovenia", "South Africa", "South Korea",
    "Spain", "Sri Lanka", "Sudan", "Sweden", "Switzerland", "Syria", "Taiwan", "Tajikistan",
    "Tanzania", "Thailand", "Trinidad and Tobago", "Tunisia", "Turkey", "Uganda", "Ukraine",
    "United Arab Emirates", "Uruguay", "Uzbekistan", "Vatican City", "Venezuela", "Vietnam",
    "Yemen", "Zambia", "Zimbabwe",
]

US_STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut",
    "Delaware", "District of Columbia", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois",
    "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland",
    "Massachusetts", "Michigan", "Minnesota", "Mississippi", "Missouri", "Montana",
    "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico", "New York",
    "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
    "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah",
    "Vermont", "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming",
]

US_STATE_ABBR = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
    "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
    "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia",
    "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}

@login_required(login_url='accounts.login')
def edit_profile(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    is_new_account = bool(request.GET.get('new') == '1' or request.session.get('is_new_account', False))
    selected_state_name = US_STATE_ABBR.get(profile.state, profile.state)
    is_us = profile.country in ['United States', 'US', 'USA']

    if request.method == 'POST':
        request.session.pop('is_new_account', None)
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        username = request.POST.get('username', '').strip()
        headline = request.POST.get('headline', '').strip()
        about = request.POST.get('about', '').strip()
        city = request.POST.get('city', '').strip()
        country = request.POST.get('country', '').strip()
        state = request.POST.get('state', '').strip()
        if country not in ['United States', 'US', 'USA']:
            state = ''

        if username and username.lower() != request.user.username.lower():
            if User.objects.filter(username__iexact=username).exists():
                messages.error(request, f'Username "{username}" is already taken.')
                template_data = {'title': 'Edit Your Profile | LockedIn'}
                return render(request, 'accounts/edit_profile.html', {
                    'template_data': template_data,
                    'profile': profile,
                    'profile_user': request.user,
                    'is_owner': True,
                    'is_new_account': is_new_account,
                    'countries': COUNTRIES,
                    'us_states': US_STATES,
                    'selected_state_name': selected_state_name,
                    'is_us': is_us,
                })
            request.user.username = username

        request.user.first_name = first_name
        request.user.last_name = last_name
        request.user.save()

        if request.POST.get('remove_photo') == 'on':
            if profile.photo:
                profile.photo.delete(save=False)
            profile.photo = None
        elif 'photo' in request.FILES:
            profile.photo = request.FILES['photo']

        profile.headline = headline
        profile.about = about
        if 'education' in request.POST:
            profile.education = request.POST.get('education', '').strip()
        if 'experience' in request.POST:
            profile.experience = request.POST.get('experience', '').strip()
        if 'skills' in request.POST:
            profile.skills = request.POST.get('skills', '').strip()
        if 'projects' in request.POST:
            profile.projects = request.POST.get('projects', '').strip()
        profile.city = city
        profile.state = state
        profile.country = country
        profile.update_location_string()
        profile.is_private = 'is_private' in request.POST
        profile.show_email = 'show_email' in request.POST
        profile.show_location = 'show_location' in request.POST
        profile.show_education = 'show_education' in request.POST
        profile.show_experience = 'show_experience' in request.POST
        profile.show_skills = 'show_skills' in request.POST
        profile.show_projects = 'show_projects' in request.POST
        profile.save()

        from leveling.services import award_profile_completed_achievement
        first_time_result = award_profile_completed_achievement(request.user)

        if first_time_result:
            request.session['show_locked_in_modal'] = True

        messages.success(request, 'Your profile has been saved!')
        return redirect('accounts.profile', username=request.user.username)

    template_data = {'title': 'Edit Your Profile | LockedIn'}
    return render(request, 'accounts/edit_profile.html', {
        'template_data': template_data,
        'profile': profile,
        'profile_user': request.user,
        'is_owner': True,
        'is_new_account': is_new_account,
        'countries': COUNTRIES,
        'us_states': US_STATES,
        'selected_state_name': selected_state_name,
        'is_us': is_us,
    })

def user_profile(request, username):
    user = get_object_or_404(User, username__iexact=username)
    profile, _ = Profile.objects.get_or_create(user=user)

    full_name = user.get_full_name()
    if not full_name:
        full_name = user.username

    template_data = {
        'title': f"{full_name} | LockedIn",
    }

    is_owner = request.user.is_authenticated and request.user == user
    is_admin = request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)
    can_view_profile = not profile.is_private or is_owner or is_admin

    show_locked_in_modal = False
    level_profile = None
    if is_owner:
        show_locked_in_modal = request.session.pop('show_locked_in_modal', False)
        if show_locked_in_modal:
            from leveling.services import get_or_create_user_level_profile
            level_profile = get_or_create_user_level_profile(request.user)

    return render(request, 'accounts/profile.html', {
        'template_data': template_data,
        'profile_user': user,
        'profile': profile,
        'full_name': full_name,
        'is_owner': is_owner,
        'is_admin': is_admin,
        'can_view_profile': can_view_profile,
        'show_locked_in_modal': show_locked_in_modal,
        'level_profile': level_profile,
    })

def parse_date_input(val):
    if not val:
        return None
    try:
        from datetime import date
        return date.fromisoformat(val)
    except (ValueError, TypeError):
        return None

def sync_profile_summaries(profile):
    profile.skills = ", ".join(s.name for s in profile.skills_list.all())
    profile.projects = ", ".join(p.title for p in profile.projects_list.all())
    profile.save(update_fields=['skills', 'projects'])

@login_required(login_url='accounts.login')
def add_education(request):
    if request.method == 'POST':
        school = request.POST.get('school', '').strip()
        degree = request.POST.get('degree', '').strip()
        major = request.POST.get('major', '').strip()
        gpa = request.POST.get('gpa', '').strip()
        start_date = parse_date_input(request.POST.get('start_date', '').strip())
        is_current = 'is_current' in request.POST
        end_date = None if is_current else parse_date_input(request.POST.get('end_date', '').strip())
        description = request.POST.get('description', '').strip()

        if not school:
            messages.error(request, 'School name is required.')
        else:
            profile, _ = Profile.objects.get_or_create(user=request.user)
            edu = Education(
                profile=profile,
                school=school,
                degree=degree,
                major=major,
                gpa=gpa,
                start_date=start_date,
                end_date=end_date,
                is_current=is_current,
                description=description,
            )
            edu.enrollment_period = edu.format_period()
            edu.save()
            messages.success(request, 'Education entry added.')

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or redirect('accounts.edit_profile').url
    return redirect(next_url)

@login_required(login_url='accounts.login')
def edit_education(request, item_id):
    item = get_object_or_404(Education, id=item_id, profile__user=request.user)
    if request.method == 'POST':
        school = request.POST.get('school', '').strip()
        if not school:
            messages.error(request, 'School name is required.')
        else:
            item.school = school
            item.degree = request.POST.get('degree', '').strip()
            item.major = request.POST.get('major', '').strip()
            item.gpa = request.POST.get('gpa', '').strip()
            item.start_date = parse_date_input(request.POST.get('start_date', '').strip())
            item.is_current = 'is_current' in request.POST
            item.end_date = None if item.is_current else parse_date_input(request.POST.get('end_date', '').strip())
            item.description = request.POST.get('description', '').strip()
            item.enrollment_period = item.format_period()
            item.save()
            messages.success(request, 'Education entry updated.')
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or redirect('accounts.edit_profile').url
    return redirect(next_url)

@login_required(login_url='accounts.login')
def delete_education(request, item_id):
    if request.method == 'POST':
        item = get_object_or_404(Education, id=item_id, profile__user=request.user)
        item.delete()
        messages.info(request, 'Education entry removed.')
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or redirect('accounts.edit_profile').url
    return redirect(next_url)

@login_required(login_url='accounts.login')
def add_experience(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        company = request.POST.get('company', '').strip()
        location = request.POST.get('location', '').strip()
        start_date = parse_date_input(request.POST.get('start_date', '').strip())
        is_current = 'is_current' in request.POST
        end_date = None if is_current else parse_date_input(request.POST.get('end_date', '').strip())
        description = request.POST.get('description', '').strip()

        if not title or not company:
            messages.error(request, 'Job title and company name are required.')
        else:
            profile, _ = Profile.objects.get_or_create(user=request.user)
            exp = Experience(
                profile=profile,
                title=title,
                company=company,
                location=location,
                start_date=start_date,
                end_date=end_date,
                is_current=is_current,
                description=description,
            )
            exp.period = exp.format_period()
            exp.save()
            messages.success(request, 'Experience entry added.')

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or redirect('accounts.edit_profile').url
    return redirect(next_url)

@login_required(login_url='accounts.login')
def edit_experience(request, item_id):
    item = get_object_or_404(Experience, id=item_id, profile__user=request.user)
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        company = request.POST.get('company', '').strip()
        if not title or not company:
            messages.error(request, 'Job title and company name are required.')
        else:
            item.title = title
            item.company = company
            item.location = request.POST.get('location', '').strip()
            item.start_date = parse_date_input(request.POST.get('start_date', '').strip())
            item.is_current = 'is_current' in request.POST
            item.end_date = None if item.is_current else parse_date_input(request.POST.get('end_date', '').strip())
            item.description = request.POST.get('description', '').strip()
            item.period = item.format_period()
            item.save()
            messages.success(request, 'Experience entry updated.')
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or redirect('accounts.edit_profile').url
    return redirect(next_url)

@login_required(login_url='accounts.login')
def delete_experience(request, item_id):
    if request.method == 'POST':
        item = get_object_or_404(Experience, id=item_id, profile__user=request.user)
        item.delete()
        messages.info(request, 'Experience entry removed.')
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or redirect('accounts.edit_profile').url
    return redirect(next_url)

@login_required(login_url='accounts.login')
def add_skill(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        proficiency = request.POST.get('proficiency', '').strip()

        if not name:
            messages.error(request, 'Skill name is required.')
        else:
            profile, _ = Profile.objects.get_or_create(user=request.user)
            Skill.objects.create(
                profile=profile,
                name=name,
                proficiency=proficiency,
            )
            sync_profile_summaries(profile)
            messages.success(request, 'Skill added.')

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or redirect('accounts.edit_profile').url
    return redirect(next_url)

@login_required(login_url='accounts.login')
def edit_skill(request, item_id):
    item = get_object_or_404(Skill, id=item_id, profile__user=request.user)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'Skill name is required.')
        else:
            item.name = name
            item.proficiency = request.POST.get('proficiency', '').strip()
            item.save()
            sync_profile_summaries(item.profile)
            messages.success(request, 'Skill updated.')
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or redirect('accounts.edit_profile').url
    return redirect(next_url)

@login_required(login_url='accounts.login')
def delete_skill(request, item_id):
    if request.method == 'POST':
        item = get_object_or_404(Skill, id=item_id, profile__user=request.user)
        profile = item.profile
        item.delete()
        sync_profile_summaries(profile)
        messages.info(request, 'Skill removed.')
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or redirect('accounts.edit_profile').url
    return redirect(next_url)

@login_required(login_url='accounts.login')
def add_project(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        technologies = request.POST.get('technologies', '').strip()
        link = request.POST.get('link', '').strip()
        description = request.POST.get('description', '').strip()

        if not title:
            messages.error(request, 'Project title is required.')
        else:
            profile, _ = Profile.objects.get_or_create(user=request.user)
            Project.objects.create(
                profile=profile,
                title=title,
                technologies=technologies,
                link=link,
                description=description,
            )
            sync_profile_summaries(profile)
            messages.success(request, 'Project added.')

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or redirect('accounts.edit_profile').url
    return redirect(next_url)

@login_required(login_url='accounts.login')
def edit_project(request, item_id):
    item = get_object_or_404(Project, id=item_id, profile__user=request.user)
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if not title:
            messages.error(request, 'Project title is required.')
        else:
            item.title = title
            item.technologies = request.POST.get('technologies', '').strip()
            item.link = request.POST.get('link', '').strip()
            item.description = request.POST.get('description', '').strip()
            item.save()
            sync_profile_summaries(item.profile)
            messages.success(request, 'Project updated.')
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or redirect('accounts.edit_profile').url
    return redirect(next_url)

@login_required(login_url='accounts.login')
def delete_project(request, item_id):
    if request.method == 'POST':
        item = get_object_or_404(Project, id=item_id, profile__user=request.user)
        profile = item.profile
        item.delete()
        sync_profile_summaries(profile)
        messages.info(request, 'Project removed.')
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or redirect('accounts.edit_profile').url
    return redirect(next_url)