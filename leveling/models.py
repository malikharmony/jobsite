from django.db import models
from django.conf import settings
from django.utils import timezone


LEVEL_TITLES = {
    1: "Job Seeker Novice",
    2: "Resume Ready",
    3: "Active Applicant",
    4: "Interview Candidate",
    5: "Network Climber",
    6: "Career Crusader",
    7: "Market Veteran",
    8: "Locked In Legend",
}

LEVEL_THRESHOLDS = [
    (1, 0),
    (2, 100),
    (3, 250),
    (4, 500),
    (5, 850),
    (6, 1300),
    (7, 1850),
    (8, 2500),
]


class UserLevelProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='level_profile'
    )
    xp = models.PositiveIntegerField(default=0)
    level = models.PositiveIntegerField(default=1)

    # Activity metric counters
    total_applications = models.PositiveIntegerField(default=0)
    distinct_companies_applied = models.PositiveIntegerField(default=0)
    interviews_count = models.PositiveIntegerField(default=0)
    offers_count = models.PositiveIntegerField(default=0)
    rejections_count = models.PositiveIntegerField(default=0)
    profile_updates_count = models.PositiveIntegerField(default=0)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - Level {self.level} ({self.xp} XP)"

    @classmethod
    def threshold_for_level(cls, level_num):
        if level_num <= 1:
            return 0
        for lvl, req in LEVEL_THRESHOLDS:
            if lvl == level_num:
                return req
        # Extrapolate beyond level 8: 2500 + (level - 8) * 750
        return 2500 + (level_num - 8) * 750

    @property
    def rank_title(self):
        if self.level in LEVEL_TITLES:
            return LEVEL_TITLES[self.level]
        return "Locked In Legend"

    @property
    def current_level_floor_xp(self):
        return self.threshold_for_level(self.level)

    @property
    def next_level_threshold_xp(self):
        return self.threshold_for_level(self.level + 1)

    @property
    def xp_progress_in_current_level(self):
        floor = self.current_level_floor_xp
        return max(0, self.xp - floor)

    @property
    def xp_needed_for_next_level(self):
        ceil = self.next_level_threshold_xp
        floor = self.current_level_floor_xp
        return max(1, ceil - floor)

    @property
    def level_progress_percentage(self):
        span = self.xp_needed_for_next_level
        earned = self.xp_progress_in_current_level
        pct = int(min(100, max(0, (earned / span) * 100)))
        return pct

    def calculate_level_from_xp(self):
        current_lvl = 1
        # Check through defined thresholds
        for lvl, req in LEVEL_THRESHOLDS:
            if self.xp >= req:
                current_lvl = lvl
            else:
                break
        if self.xp >= 2500:
            extra = (self.xp - 2500) // 750
            current_lvl = 8 + extra
        return current_lvl

    def add_xp(self, amount):
        if amount <= 0:
            return False
        self.xp += amount
        new_level = self.calculate_level_from_xp()
        leveled_up = new_level > self.level
        self.level = new_level
        self.save(update_fields=['xp', 'level', 'updated_at'])
        return leveled_up


class Achievement(models.Model):
    CATEGORY_CHOICES = [
        ('milestone', 'Milestone'),
        ('novelty', 'Novelty & Humor'),
        ('profile', 'Profile'),
        ('special', 'Special'),
    ]

    slug = models.SlugField(max_length=100, unique=True)
    title = models.CharField(max_length=150)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='milestone')
    icon = models.CharField(max_length=100, default='fa-solid fa-award')
    xp_reward = models.PositiveIntegerField(default=100)
    target_value = models.PositiveIntegerField(default=1)
    metric_key = models.CharField(
        max_length=100,
        help_text="Key matching metric/rule, e.g. 'total_applications', 'rejected_after_internship'"
    )
    is_secret = models.BooleanField(
        default=False,
        help_text="Hidden/masked until unlocked"
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ('order', 'title')

    def __str__(self):
        return f"{self.title} (+{self.xp_reward} XP)"


class UserAchievement(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_achievements'
    )
    achievement = models.ForeignKey(
        Achievement,
        on_delete=models.CASCADE,
        related_name='user_progress'
    )
    current_progress = models.PositiveIntegerField(default=0)
    unlocked = models.BooleanField(default=False)
    unlocked_at = models.DateTimeField(null=True, blank=True)
    viewed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'achievement')
        ordering = ('-unlocked', 'achievement__order')

    def __str__(self):
        status = "Unlocked" if self.unlocked else f"{self.current_progress}/{self.achievement.target_value}"
        return f"{self.user.username} - {self.achievement.title} ({status})"

    @property
    def progress_percentage(self):
        if self.unlocked:
            return 100
        if not self.achievement.target_value:
            return 0
        return min(100, int((self.current_progress / self.achievement.target_value) * 100))


class Quest(models.Model):
    TYPE_CHOICES = [
        ('weekly', 'Weekly Quest'),
        ('daily', 'Daily Quest'),
        ('one_time', 'One-Time Quest'),
    ]

    slug = models.SlugField(max_length=100, unique=True)
    title = models.CharField(max_length=150)
    description = models.TextField()
    quest_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default='weekly')
    metric_key = models.CharField(max_length=100)
    target_count = models.PositiveIntegerField(default=1)
    xp_reward = models.PositiveIntegerField(default=100)
    icon = models.CharField(max_length=100, default='fa-solid fa-compass')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"[{self.get_quest_type_display()}] {self.title} (+{self.xp_reward} XP)"


class UserQuest(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_quests'
    )
    quest = models.ForeignKey(
        Quest,
        on_delete=models.CASCADE,
        related_name='user_instances'
    )
    period_start = models.DateField()
    period_end = models.DateField()
    progress = models.PositiveIntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_reward_claimed = models.BooleanField(default=False)
    claimed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'quest', 'period_start')
        ordering = ('is_reward_claimed', '-is_completed', '-period_start')

    def __str__(self):
        status = "Claimed" if self.is_reward_claimed else ("Completed" if self.is_completed else f"{self.progress}/{self.quest.target_count}")
        return f"{self.user.username} - {self.quest.title} ({status})"

    @property
    def progress_percentage(self):
        if self.is_completed:
            return 100
        if not self.quest.target_count:
            return 0
        return min(100, int((self.progress / self.quest.target_count) * 100))
