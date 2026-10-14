from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='accounts.index'),
    path('signup/', views.signup, name='accounts.signup'),
    path('login/', views.login_view, name='accounts.login'),
    path('logout/', views.logout_view, name='accounts.logout'),
    path('profile/edit/', views.edit_profile, name='accounts.edit_profile'),
    path('profile/education/add/', views.add_education, name='accounts.add_education'),
    path('profile/education/<int:item_id>/edit/', views.edit_education, name='accounts.edit_education'),
    path('profile/education/<int:item_id>/delete/', views.delete_education, name='accounts.delete_education'),
    path('profile/experience/add/', views.add_experience, name='accounts.add_experience'),
    path('profile/experience/<int:item_id>/edit/', views.edit_experience, name='accounts.edit_experience'),
    path('profile/experience/<int:item_id>/delete/', views.delete_experience, name='accounts.delete_experience'),
    path('profile/skill/add/', views.add_skill, name='accounts.add_skill'),
    path('profile/skill/<int:item_id>/edit/', views.edit_skill, name='accounts.edit_skill'),
    path('profile/skill/<int:item_id>/delete/', views.delete_skill, name='accounts.delete_skill'),
    path('profile/project/add/', views.add_project, name='accounts.add_project'),
    path('profile/project/<int:item_id>/edit/', views.edit_project, name='accounts.edit_project'),
    path('profile/project/<int:item_id>/delete/', views.delete_project, name='accounts.delete_project'),
]