from .models import UserAchievement, UserQuest


def unviewed_achievements_processor(request):
    """Makes any newly unlocked, unviewed achievements and completed quests available to all templates."""
    if not request.user.is_authenticated:
        return {}

    unviewed_achievements = UserAchievement.objects.filter(
        user=request.user,
        unlocked=True,
        viewed=False
    ).select_related('achievement')

    unviewed_quests = UserQuest.objects.filter(
        user=request.user,
        is_completed=True,
        notified=False
    ).select_related('quest')

    return {
        'unviewed_achievements': list(unviewed_achievements),
        'unviewed_quests': list(unviewed_quests),
    }
