from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='jobs.index'),
    path('applications/', views.applications, name='jobs.applications'),
    path('for-you/', views.for_you, name='jobs.for_you'),
    path('create/', views.create_job, name='jobs.create'),
    path('mine/', views.my_jobs, name='jobs.my_jobs'),
    path('<int:id>/applicants/', views.applicants, name='jobs.applicants'),
    path('<int:id>/apply/', views.apply, name='jobs.apply'),
    path('<int:id>/report/', views.report_job, name='jobs.report'),
    path('<int:id>/', views.detail, name='jobs.detail'),
    path('<int:id>/edit/', views.edit_job, name='jobs.edit'),
]