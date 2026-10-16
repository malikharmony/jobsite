from .models import UserAchievement


def unviewed_achievements_processor(request):
    """Makes any newly unlocked, unviewed achievements available to all templates."""
    if not request.user.is_authenticated:
        return {}

    unviewed = UserAchievement.objects.filter(
        user=request.user,
        unlocked=True,
        viewed=False
    ).select_related('achievement')

    return {
        'unviewed_achievements': list(unviewed)
    }

