from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Resume

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')

class ResumeUploadForm(forms.ModelForm):
    class Meta:
        model = Resume
        fields = ('file',)
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.docx'})
        }
