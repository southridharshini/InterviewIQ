from django.db import models
from django.contrib.auth.models import User


class Company(models.Model):
    """Stores company profiles along with CGPA and arrear criteria for eligibility checking."""
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    
    # CGPA & Arrears Eligibility Criteria
    min_cgpa = models.FloatField(default=0.0)
    max_active_arrears = models.IntegerField(default=0)
    max_history_arrears = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Companies"
        ordering = ['name']

    def __str__(self):
        return self.name


class JobProfile(models.Model):
    """New model added for role matching without altering existing models."""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='job_profiles', null=True, blank=True)
    company_name = models.CharField(max_length=150)
    role_title = models.CharField(max_length=150)
    required_skills = models.TextField(help_text="Comma-separated skills, e.g., python, django, sql, html, css")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['company_name', 'role_title']

    def get_skills_list(self):
        return [skill.strip().lower() for skill in self.required_skills.split(',') if skill.strip()]

    def __str__(self):
        return f"{self.company_name} - {self.role_title}"


class InterviewExperience(models.Model):
    """Stores student interview experiences, questions, outcomes, and spam flags."""
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    ]

    OUTCOME_CHOICES = [
        ('Cleared', 'Cleared'),
        ('Not Cleared', 'Not Cleared'),
        ('Pending', 'Pending'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='experiences')
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name='experiences')
    company_name = models.CharField(max_length=150)  # Standardized string field
    role = models.CharField(max_length=150)
    
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES)
    outcome = models.CharField(max_length=20, choices=OUTCOME_CHOICES)
    elimination_round = models.CharField(max_length=50, blank=True, null=True)
    
    experience = models.TextField()
    questions_asked = models.TextField(blank=True, null=True)
    tips = models.TextField(blank=True, null=True)
    
    resume_file = models.FileField(upload_to='resumes/', blank=True, null=True)
    generated_badge = models.CharField(max_length=255, blank=True, null=True)
    is_spam = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.company_name} ({self.role})"


class ResumeAnalysis(models.Model):
    """Stores candidate resume scoring history for dashboard analytics."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='resume_analyses')
    company_name = models.CharField(max_length=150)
    role = models.CharField(max_length=150)
    skills = models.TextField(help_text="Detected comma-separated skills")
    projects = models.TextField(help_text="Extracted project summary preview")
    match_score = models.FloatField()
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Resume Analyses"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.company_name} Match Score: {self.match_score}%"