from django.urls import path
from . import views

app_name = 'leveling'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('claim/<int:user_quest_id>/', views.claim_reward, name='claim_reward'),
]

