from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    """
    Custom User model for AI Interview Preparation Assistant.
    Extends AbstractUser which already provides:
    - username, first_name, last_name, email, password, etc.
    """
    pass

class Resume(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='resumes', db_index=True)
    file = models.FileField(upload_to='resumes/')
    uploaded_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Parsed data fields
    parsed_skills = models.TextField(blank=True, null=True)
    parsed_education = models.TextField(blank=True, null=True)
    parsed_experience = models.TextField(blank=True, null=True)
    parsed_projects = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Resume of {self.user.username} uploaded on {self.uploaded_at.strftime('%Y-%m-%d')}"

class Interview(models.Model):
    INTERVIEW_TYPES = [
        ('Technical', 'Technical'),
        ('HR', 'HR'),
        ('Project', 'Project-Based'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='interviews', db_index=True)
    resume = models.ForeignKey(Resume, on_delete=models.SET_NULL, null=True, blank=True)
    interview_type = models.CharField(max_length=50, choices=INTERVIEW_TYPES)
    status = models.CharField(max_length=20, default='Pending', choices=[('Pending', 'Pending'), ('Completed', 'Completed')])
    overall_score = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    def __str__(self):
        return f"{self.interview_type} Interview for {self.user.username}"

class Question(models.Model):
    interview = models.ForeignKey(Interview, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    order = models.IntegerField(default=0)
    
    def __str__(self):
        return f"Q{self.order}: {self.text[:50]}..."

class Response(models.Model):
    question = models.OneToOneField(Question, on_delete=models.CASCADE, related_name='response')
    answer_text = models.TextField(blank=True, null=True)
    
    # Granular scores as per TRD
    technical_score = models.FloatField(null=True, blank=True)
    relevance_score = models.FloatField(null=True, blank=True)
    communication_score = models.FloatField(null=True, blank=True)
    grammar_score = models.FloatField(null=True, blank=True)
    confidence_score = models.FloatField(null=True, blank=True)
    
    overall_score = models.FloatField(null=True, blank=True)
    feedback = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Response to {self.question}"

