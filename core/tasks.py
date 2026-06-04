from celery import shared_task
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .utils import generate_interview_questions, evaluate_answer
from .models import Interview, Question, Response

@shared_task
def generate_interview_questions_async(resume_data, interview_type, interview_id):
    questions_list = generate_interview_questions(resume_data, interview_type)
    interview = Interview.objects.get(id=interview_id)
    
    for i, q_text in enumerate(questions_list):
        Question.objects.create(
            interview=interview,
            text=q_text,
            order=i+1
        )
    
    # Notify frontend via Channels
    channel_layer = get_channel_layer()
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            f"interview_{interview.user.id}",
            {
                "type": "interview_message",
                "message": "Questions generated successfully",
                "interview_id": interview_id
            }
        )

@shared_task
def evaluate_answer_async(question_id, answer_text):
    question = Question.objects.get(id=question_id)
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
    
    channel_layer = get_channel_layer()
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            f"interview_{question.interview.user.id}",
            {
                "type": "evaluation_message",
                "question_id": question_id,
                "evaluation": eval_data
            }
        )
