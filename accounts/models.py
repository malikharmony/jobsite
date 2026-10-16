from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

class Profile(models.Model):
    ROLE_CHOICES = [
        ('job_seeker', 'Job Seeker'),
        ('employer', 'Employer'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='job_seeker')
    company_name = models.CharField(max_length=255, blank=True, default='')
    website = models.URLField(max_length=500, blank=True, default='')
    photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True)
    headline = models.CharField(max_length=255, blank=True, default='')
    about = models.TextField(blank=True, default='')
    education = models.TextField(blank=True, default='')
    experience = models.TextField(blank=True, default='')
    skills = models.TextField(blank=True, default='')
    projects = models.TextField(blank=True, default='')
    city = models.CharField(max_length=100, blank=True, default='')
    state = models.CharField(max_length=100, blank=True, default='')
    country = models.CharField(max_length=100, blank=True, default='')
    location = models.CharField(blank=True, default='', max_length=255)
    is_private = models.BooleanField(default=False)
    show_email = models.BooleanField(default=False)
    show_location = models.BooleanField(default=True)
    show_education = models.BooleanField(default=True)
    show_experience = models.BooleanField(default=True)
    show_skills = models.BooleanField(default=True)
    show_projects = models.BooleanField(default=True)

    def update_location_string(self):
        parts = [p for p in [self.city, self.state, self.country] if p]
        self.location = ", ".join(parts)

    @property
    def display_name(self):
        if self.role == 'employer' and self.company_name:
            return self.company_name
        return self.user.get_full_name() or self.user.username

    def __str__(self):
        return f"{self.user.username}'s Profile"


class Education(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='educations')
    school = models.CharField(max_length=255)
    degree = models.CharField(max_length=255, blank=True, default='')
    major = models.CharField(max_length=255, blank=True, default='')
    gpa = models.CharField(max_length=50, blank=True, default='')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    enrollment_period = models.CharField(max_length=100, blank=True, default='')
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    def format_period(self):
        if self.start_date:
            start_str = self.start_date.strftime('%b %Y')
            if self.is_current:
                return f"{start_str} - Present"
            if self.end_date:
                return f"{start_str} - {self.end_date.strftime('%b %Y')}"
            return start_str
        if self.is_current:
            return "Present"
        return self.enrollment_period

    def __str__(self):
        return f"{self.school} - {self.profile.user.username}"


class Experience(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='experiences')
    title = models.CharField(max_length=255)
    company = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True, default='')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    period = models.CharField(max_length=100, blank=True, default='')
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    def format_period(self):
        if self.start_date:
            start_str = self.start_date.strftime('%b %Y')
            if self.is_current:
                return f"{start_str} - Present"
            if self.end_date:
                return f"{start_str} - {self.end_date.strftime('%b %Y')}"
            return start_str
        if self.is_current:
            return "Present"
        return self.period

    def __str__(self):
        return f"{self.title} at {self.company} - {self.profile.user.username}"


class Skill(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='skills_list')
    name = models.CharField(max_length=100)
    proficiency = models.CharField(max_length=50, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('created_at',)

    def __str__(self):
        return f"{self.name} - {self.profile.user.username}"


class Project(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='projects_list')
    title = models.CharField(max_length=255)
    technologies = models.CharField(max_length=255, blank=True, default='')
    link = models.URLField(max_length=500, blank=True, default='')
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f"{self.title} - {self.profile.user.username}"


class Report(models.Model):


    # self explanatory
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('under_review', 'Under review'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    ]

    # the reporter
    reporter = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submitted_reports',
    )

    # what did they report
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name='moderation_reports',
    )
    object_id = models.PositiveBigIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    reason = models.CharField(max_length=100)
    details = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True)
    # tells us who reviewed the report (an admin)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_reports',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ('status', '-created_at')

    #stringify to the status and report about the target
    def __str__(self):
        target = self.content_object or f'{self.content_type} #{self.object_id}'
        return f'{self.get_status_display()} report about {target}'
