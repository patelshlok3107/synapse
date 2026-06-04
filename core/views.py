from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.cache import cache
import json
import os
import uuid
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .forms import CustomUserCreationForm, ResumeUploadForm
from .models import Resume, Interview, Question, Response
from .utils import extract_text_from_file, parse_resume_with_gemini, generate_interview_questions, evaluate_answer, transcribe_audio_with_whisper

def home(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard') # We will create dashboard later
    return render(request, 'core/home.html')

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now log in.')
            return redirect('core:login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'core/register.html', {'form': form})

@login_required
def dashboard(request):
    # Try to get from cache first
    cache_key = f'dashboard_metrics_{request.user.id}'
    cached_metrics = cache.get(cache_key)
    
    if cached_metrics:
        total_interviews = cached_metrics['total_interviews']
        avg_score = cached_metrics['avg_score']
    else:
        completed_interviews = request.user.interviews.filter(status='Completed')
        total_interviews = completed_interviews.count()
        
        if total_interviews > 0:
            avg_score = sum([i.overall_score for i in completed_interviews if i.overall_score]) / total_interviews
            avg_score = round(avg_score, 1)
        else:
            avg_score = 0
            
        cache.set(cache_key, {'total_interviews': total_interviews, 'avg_score': avg_score}, 60*5) # cache for 5 min
        
    resumes = request.user.resumes.all().order_by('-uploaded_at')
    interviews = request.user.interviews.all().order_by('-created_at')
        
    return render(request, 'core/dashboard.html', {
        'resumes': resumes,
        'interviews': interviews,
        'total_interviews': total_interviews,
        'avg_score': avg_score
    })

@login_required
def upload_resume(request):
    if request.method == 'POST':
        form = ResumeUploadForm(request.POST, request.FILES)
        if form.is_valid():
            resume = form.save(commit=False)
            resume.user = request.user
            resume.save()
            
            # Process and parse resume
            try:
                text = extract_text_from_file(resume.file.path)
                parsed_data = parse_resume_with_gemini(text)
                
                resume.parsed_skills = parsed_data.get('skills', '')
                resume.parsed_education = parsed_data.get('education', '')
                resume.parsed_experience = parsed_data.get('experience', '')
                resume.parsed_projects = parsed_data.get('projects', '')
                resume.save()
                
                if 'error' in parsed_data:
                    messages.warning(request, parsed_data['error'])
                else:
                    messages.success(request, 'Resume uploaded and parsed successfully!')
            except Exception as e:
                messages.error(request, f'Error parsing resume: {str(e)}')
                
            return redirect('core:resume_detail', resume_id=resume.id)
    else:
        form = ResumeUploadForm()
    return render(request, 'core/upload_resume.html', {'form': form})

@login_required
def resume_detail(request, resume_id):
    resume = get_object_or_404(Resume, id=resume_id, user=request.user)
    return render(request, 'core/resume_detail.html', {'resume': resume})

@login_required
def start_interview(request):
    if request.method == 'POST':
        resume_id = request.POST.get('resume_id')
        interview_type = request.POST.get('interview_type')
        
        resume = None
        if resume_id:
            resume = get_object_or_404(Resume, id=resume_id, user=request.user)
            resume_data = {
                'parsed_skills': resume.parsed_skills,
                'parsed_experience': resume.parsed_experience,
                'parsed_projects': resume.parsed_projects
            }
        else:
            resume_data = {}
            
        questions_list = generate_interview_questions(resume_data, interview_type)
        
        # Create Interview record
        interview = Interview.objects.create(
            user=request.user,
            resume=resume,
            interview_type=interview_type,
            status='Pending'
        )
        
        # Create Question records
        for i, q_text in enumerate(questions_list):
            Question.objects.create(
                interview=interview,
                text=q_text,
                order=i+1
            )
            
        return redirect('core:interview_session', interview_id=interview.id)
        
    resumes = request.user.resumes.all().order_by('-uploaded_at')
    return render(request, 'core/start_interview.html', {'resumes': resumes, 'types': Interview.INTERVIEW_TYPES})

@login_required
def interview_session(request, interview_id):
    interview = get_object_or_404(Interview, id=interview_id, user=request.user)
    questions = interview.questions.all().order_by('order')
    return render(request, 'core/interview_session.html', {'interview': interview, 'questions': questions})

@login_required
@require_POST
def submit_answer(request, question_id):
    question = get_object_or_404(Question, id=question_id, interview__user=request.user)
    
    try:
        data = json.loads(request.body)
        answer_text = data.get('answer_text', '')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    if not answer_text:
        return JsonResponse({'error': 'Answer cannot be empty'}, status=400)
        
    eval_data = evaluate_answer(question.text, answer_text)
    
    response_obj, created = Response.objects.update_or_create(
        question=question,
        defaults={
            'answer_text': answer_text,
            'technical_score': eval_data.get('technical_score', 0),
            'relevance_score': eval_data.get('relevance_score', 0),
            'communication_score': eval_data.get('communication_score', 0),
            'grammar_score': eval_data.get('grammar_score', 0),
            'confidence_score': eval_data.get('confidence_score', 0),
            'overall_score': eval_data.get('overall_score', 0),
            'feedback': eval_data.get('feedback', '')
        }
    )
    
    interview = question.interview
    total_q = interview.questions.count()
    answered_q = Response.objects.filter(question__interview=interview).count()
    
    is_complete = False
    if total_q == answered_q:
        interview.status = 'Completed'
        avg = sum([r.overall_score for r in Response.objects.filter(question__interview=interview) if r.overall_score is not None]) / total_q
        interview.overall_score = avg
        interview.save()
        is_complete = True
        
    return JsonResponse({
        'success': True,
        'evaluation': eval_data,
        'is_complete': is_complete
    })

@login_required
@require_POST
def upload_audio(request):
    if 'audio' not in request.FILES:
        return JsonResponse({'error': 'No audio file provided'}, status=400)
        
    audio_file = request.FILES['audio']
    # Save the file temporarily
    filename = f"temp_audio_{uuid.uuid4().hex}.webm"
    path = default_storage.save(f"temp/{filename}", ContentFile(audio_file.read()))
    full_path = os.path.join(default_storage.location, path)
    
    try:
        # Transcribe
        text = transcribe_audio_with_whisper(full_path)
    finally:
        # Cleanup
        if os.path.exists(full_path):
            os.remove(full_path)
            
    if text is None:
        return JsonResponse({'error': 'Transcription failed. (Ensure OPENAI_API_KEY is set for Whisper)'}, status=500)
        
    return JsonResponse({'success': True, 'text': text})

def products(request):
    return render(request, 'core/products.html')

def solutions(request):
    return render(request, 'core/solutions.html')

def resources(request):
    return render(request, 'core/resources.html')

from django.http import StreamingHttpResponse

@login_required
@require_POST
def chatbot(request):
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    if not user_message.strip():
        return JsonResponse({'error': 'Message cannot be empty'}, status=400)
    
    from .utils import chat_with_ai_stream
    return StreamingHttpResponse(chat_with_ai_stream(user_message, request.user.username), content_type='text/plain')
