from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from .models import UserQuest, UserAchievement
from .services import (
    get_or_create_user_level_profile,
    ensure_user_quests,
    ensure_user_achievements,
    claim_quest_reward,
)


@login_required
def dashboard(request):
    """Main gamification dashboard displaying user level, active weekly quests, and achievements."""
    user = request.user
    level_profile = get_or_create_user_level_profile(user)
    quests = ensure_user_quests(user)
    achievements = ensure_user_achievements(user)

    completed_quests = quests.filter(is_completed=True).count()
    unlocked_achievements = achievements.filter(unlocked=True).count()
    total_achievements = achievements.count()

    template_data = {
        'title': 'Leveling & Quests | LockedIn',
    }

    return render(request, 'leveling/dashboard.html', {
        'template_data': template_data,
        'level_profile': level_profile,
        'quests': quests,
        'achievements': achievements,
        'completed_quests': completed_quests,
        'unlocked_achievements': unlocked_achievements,
        'total_achievements': total_achievements,
    })


@login_required
@require_POST
def claim_reward(request, user_quest_id):
    """Claim XP reward for an accomplished quest."""
    success, msg, leveled_up = claim_quest_reward(request.user, user_quest_id)
    if success:
        if leveled_up:
            level_profile = get_or_create_user_level_profile(request.user)
            messages.success(
                request,
                f"🎉 {msg} LEVEL UP! You reached Level {level_profile.level}: {level_profile.rank_title}!"
            )
        else:
            messages.success(request, f"✨ {msg}")
    else:
        messages.error(request, msg)

    return redirect('leveling:dashboard')


@login_required
def get_unviewed_achievements(request):
    """API endpoint polled by client to fetch newly unlocked achievements."""
    unviewed = UserAchievement.objects.filter(
        user=request.user,
        unlocked=True,
        viewed=False
    ).select_related('achievement')

    data = [
        {
            'id': ua.id,
            'title': ua.achievement.title,
            'description': ua.achievement.description,
            'icon': ua.achievement.icon,
            'xp_reward': ua.achievement.xp_reward,
            'category': ua.achievement.get_category_display(),
        }
        for ua in unviewed
    ]
    return JsonResponse({'achievements': data})


@login_required
def mark_achievement_viewed(request, user_achievement_id):
    """API endpoint to acknowledge and mark an unlocked achievement as viewed."""
    updated = UserAchievement.objects.filter(
        id=user_achievement_id,
        user=request.user
    ).update(viewed=True)
    return JsonResponse({'success': bool(updated)})
