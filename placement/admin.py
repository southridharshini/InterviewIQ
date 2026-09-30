from django.contrib import admin
from .models import Company, JobProfile, InterviewExperience, ResumeAnalysis


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'min_cgpa', 'max_active_arrears', 'max_history_arrears', 'created_at')
    search_fields = ('name',)
    list_filter = ('min_cgpa',)


@admin.register(JobProfile)
class JobProfileAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'role_title', 'required_skills', 'created_at')
    search_fields = ('company_name', 'role_title', 'required_skills')
    list_filter = ('company_name',)


@admin.register(InterviewExperience)
class InterviewExperienceAdmin(admin.ModelAdmin):
    list_display = ('user', 'company_name', 'role', 'outcome', 'difficulty', 'created_at')
    list_filter = ('outcome', 'difficulty', 'company_name')
    search_fields = ('company_name', 'role', 'user__username', 'experience')


@admin.register(ResumeAnalysis)
class ResumeAnalysisAdmin(admin.ModelAdmin):
    list_display = ('user', 'company_name', 'role', 'match_score', 'created_at')
    list_filter = ('company_name',)