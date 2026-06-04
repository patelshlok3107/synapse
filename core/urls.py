from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='core:login'), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('resume/upload/', views.upload_resume, name='upload_resume'),
    path('resume/<int:resume_id>/', views.resume_detail, name='resume_detail'),
    path('interview/start/', views.start_interview, name='start_interview'),
    path('interview/<int:interview_id>/session/', views.interview_session, name='interview_session'),
    path('interview/question/<int:question_id>/submit/', views.submit_answer, name='submit_answer'),
    path('interview/audio/upload/', views.upload_audio, name='upload_audio'),
    path('products/', views.products, name='products'),
    path('solutions/', views.solutions, name='solutions'),
    path('resources/', views.resources, name='resources'),
    path('chatbot/', views.chatbot, name='chatbot'),
]
