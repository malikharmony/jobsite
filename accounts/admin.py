from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BuiltInUserAdmin
from django.contrib.auth.models import User
from django.utils import timezone

from .models import Profile, Report, Education, Experience, Skill, Project


class EducationInline(admin.TabularInline):
    model = Education
    extra = 0


class ExperienceInline(admin.TabularInline):
    model = Experience
    extra = 0


class SkillInline(admin.TabularInline):
    model = Skill
    extra = 0


class ProjectInline(admin.TabularInline):
    model = Project
    extra = 0


class ProfileInline(admin.StackedInline):
    model = Profile
    extra = 0
    max_num = 1
    fieldsets = (
        ('Platform role', {'fields': ('role',)}),
        ('Professional profile', {
            'fields': ('photo', 'headline', 'about', 'education', 'experience', 'skills', 'city', 'state', 'country', 'location', 'projects'),
            'classes': ('collapse',),
        }),
        ('Privacy settings', {
            'fields': (
                'is_private', 'show_email', 'show_location',
                'show_education', 'show_experience',
                'show_skills', 'show_projects',
            ),
            'classes': ('collapse',),
        }),
    )


admin.site.unregister(User)


@admin.register(User)
class UserAdmin(BuiltInUserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'get_role', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'profile__role')
    search_fields = ('username', 'email', 'first_name', 'last_name')

    @admin.display(description='Role', ordering='profile__role')
    def get_role(self, obj):
        try:
            return obj.profile.get_role_display()
        except Profile.DoesNotExist:
            return 'Not assigned'


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    inlines = (EducationInline, ExperienceInline, SkillInline, ProjectInline)
    list_display = ('user', 'role', 'is_private', 'headline')
    list_filter = ('role', 'is_private')
    search_fields = ('user__username', 'user__email', 'headline', 'skills')
    fieldsets = (
        ('User & Role', {'fields': ('user', 'role')}),
        ('Professional Details', {
            'fields': ('photo', 'headline', 'about', 'education', 'experience', 'skills', 'city', 'state', 'country', 'location', 'projects'),
        }),
        ('Privacy Settings', {
            'fields': (
                'is_private', 'show_email', 'show_location',
                'show_education', 'show_experience',
                'show_skills', 'show_projects',
            ),
        }),
    )


@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = ('school', 'degree', 'major', 'gpa', 'enrollment_period', 'profile')
    search_fields = ('school', 'major', 'profile__user__username')


@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'location', 'period', 'profile')
    search_fields = ('title', 'company', 'profile__user__username')


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'proficiency', 'profile')
    search_fields = ('name', 'profile__user__username')


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'technologies', 'profile')
    search_fields = ('title', 'technologies', 'profile__user__username')


# ability to put reports under review
@admin.action(description='Mark selected reports as under review')
def mark_under_review(modeladmin, request, queryset):
    queryset.update(status='under_review')


# ability to resolve reports
@admin.action(description='Resolve selected reports')
def resolve_reports(modeladmin, request, queryset):
    queryset.update(
        status='resolved',
        reviewed_by=request.user,
        reviewed_at=timezone.now(),
    )

# ability to dismiss the report (when people try to report for idiotic reasons)
@admin.action(description='Dismiss selected reports')
def dismiss_reports(modeladmin, request, queryset):
    queryset.update(
        status='dismissed',
        reviewed_by=request.user,
        reviewed_at=timezone.now(),
    )

# our admin reporting abilities
@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'status', 'reason', 'reporter', 'reported_object',
        'created_at', 'reviewed_by',
    )
    list_filter = ('status', 'content_type', 'created_at')
    search_fields = (
        'reason', 'details', 'admin_notes', 'reporter__username',
        'reporter__email', 'object_id',
    )
    readonly_fields = ('created_at', 'reviewed_at', 'reviewed_by', 'reported_object')
    actions = (mark_under_review, resolve_reports, dismiss_reports)
    date_hierarchy = 'created_at'
    list_per_page = 25
    fieldsets = (
        ('Report', {'fields': ('reporter', 'content_type', 'object_id', 'reported_object', 'reason', 'details')}),
        ('Review', {'fields': ('status', 'admin_notes', 'reviewed_by', 'reviewed_at')}),
        ('Metadata', {'fields': ('created_at',)}),
    )

    @admin.display(description='Reported object')
    def reported_object(self, obj):
        return str(obj.content_object or f'{obj.content_type} #{obj.object_id}')
