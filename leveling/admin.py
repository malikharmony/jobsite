from django.contrib import admin
from .models import (
    UserLevelProfile,
    Achievement,
    UserAchievement,
    Quest,
    UserQuest,
)


@admin.register(UserLevelProfile)
class UserLevelProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'level', 'xp', 'total_applications', 'rejections_count', 'updated_at')
    search_fields = ('user__username', 'user__email')
    list_filter = ('level',)


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'target_value', 'xp_reward', 'is_secret', 'order')
    list_filter = ('category', 'is_secret')
    search_fields = ('title', 'slug', 'description')


@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ('user', 'achievement', 'current_progress', 'unlocked', 'unlocked_at')
    list_filter = ('unlocked', 'achievement__category')
    search_fields = ('user__username', 'achievement__title')


@admin.register(Quest)
class QuestAdmin(admin.ModelAdmin):
    list_display = ('title', 'quest_type', 'target_count', 'xp_reward', 'is_active')
    list_filter = ('quest_type', 'is_active')
    search_fields = ('title', 'slug', 'description')


@admin.register(UserQuest)
class UserQuestAdmin(admin.ModelAdmin):
    list_display = ('user', 'quest', 'period_start', 'progress', 'is_completed', 'is_reward_claimed')
    list_filter = ('is_completed', 'is_reward_claimed', 'period_start')
    search_fields = ('user__username', 'quest__title')
