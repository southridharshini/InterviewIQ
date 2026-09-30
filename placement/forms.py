from django import forms
from .models import InterviewExperience

class InterviewExperienceForm(forms.ModelForm):
    class Meta:
        model = InterviewExperience
        fields = ['company_name', 'role', 'difficulty', 'outcome', 'experience', 'questions_asked', 'tips']
        widgets = {
            'company_name': forms.TextInput(attrs={'placeholder': 'e.g. TCS, Infosys, Google'}),
            'role': forms.TextInput(attrs={'placeholder': 'e.g. Software Developer, Data Analyst'}),
            'experience': forms.Textarea(attrs={'placeholder': 'Describe the rounds, overall flow, and atmosphere...'}),
            'questions_asked': forms.Textarea(attrs={'placeholder': 'List key questions asked...'}),
            'tips': forms.Textarea(attrs={'placeholder': 'What preparation strategies worked best for you?'}),
        }