from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = 'web'

urlpatterns = [
    path('', views.home, name='home'),
    path('present/', views.present, name='present'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('print/lga/', views.print_lga, name='print_lga'),
    path('dashboard/', views.entry, name='entry'),
    path('dashboard/progress/', views.progress, name='progress'),
    path('dashboard/reports/', views.reports, name='reports'),
    path('dashboard/reports/export.<str:fmt>', views.export, name='export'),
    path('dashboard/history/', views.history, name='history'),
    path('dashboard/clerks/', views.clerks, name='clerks'),
]
