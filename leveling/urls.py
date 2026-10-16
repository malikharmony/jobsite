from django.urls import path
from . import views

app_name = 'leveling'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('claim/<int:user_quest_id>/', views.claim_reward, name='claim_reward'),
    path('api/unviewed/', views.get_unviewed_achievements, name='api_unviewed'),
    path('api/mark-viewed/<int:user_achievement_id>/', views.mark_achievement_viewed, name='api_mark_viewed'),
]
