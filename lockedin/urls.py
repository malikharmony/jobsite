"""
URL configuration for jobsite project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from accounts import views as accounts_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('home.urls')),
    path('jobs/', include('jobs.urls')),
    path('accounts/', include('accounts.urls')),
    path('search/', include('search.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += [
    path('<str:username>/', accounts_views.user_profile, name='accounts.profile'),
]
