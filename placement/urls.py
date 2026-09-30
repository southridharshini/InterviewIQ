from django.urls import path
from . import views

urlpatterns = [
    # Core & Auth Routes
    path('', views.home, name='home'),
    path('register/', views.register_user, name='register'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # Experience, Company & Badges Routes
    path('experiences/', views.experiences, name='experiences'),
    path('companies/', views.companies, name='companies'),
    path('company/<str:company_name>/', views.company_detail, name='company_detail'),
    path('share-experience/', views.share_experience, name='share_experience'),
    path('linkedin-badge/<int:exp_id>/', views.linkedin_badge, name='linkedin_badge'),
    path('badges/', views.user_badges, name='badges'),

    # Features & Tools
    path('resume-analyzer/', views.resume_analyzer, name='resume_analyzer'),
    path('eligibility/', views.check_eligibility, name='check_eligibility'),
    path('mock-interview/<str:company_name>/', views.start_mock_interview, name='start_mock_interview'),
]