import PyPDF2
import docx
import os
import json
from openai import OpenAI

# Try loading API key from .env if present
from dotenv import load_dotenv
load_dotenv()

# We can use the environment variable NVIDIA_API_KEY, or fallback to the provided key
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "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")
NVIDIA_MODEL = "meta/llama-3.1-8b-instruct"

def get_nvidia_client():
    return OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=NVIDIA_API_KEY
    )

def extract_text_from_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    text = ""
    if ext == '.pdf':
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    elif ext == '.docx':
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    return text

def parse_resume_with_gemini(text):
    # Function renamed internally but we keep the name to not break views.py
    # We will use Nvidia API instead of Gemini
    client = get_nvidia_client()
    
    prompt = f"""
    Extract the following information from the provided resume text and return it strictly in JSON format.
    Do not include any markdown formatting like ```json or ``` in the response. Just the raw JSON object.
    
    Required keys:
    - "skills": A brief summary or comma-separated list of technical and soft skills.
    - "education": A brief summary of educational background.
    - "experience": A brief summary of work experience or internships.
    - "projects": A brief summary of key projects.
    
    Resume Text:
    {text[:5000]}
    """
    
    try:
        completion = client.chat.completions.create(
            model=NVIDIA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1024,
        )
        response_text = completion.choices[0].message.content.strip()
        
        # Clean up any potential markdown formatting
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
            
        parsed_data = json.loads(response_text)
        return parsed_data
    except Exception as e:
        return {
            "error": f"Failed to parse with Nvidia API: {str(e)}",
            "skills": "",
            "education": "",
            "experience": "",
            "projects": ""
        }

def generate_interview_questions(resume_data, interview_type):
    client = get_nvidia_client()
    
    prompt = f"""
    You are an expert technical interviewer. Generate exactly 5 interview questions for a {interview_type} interview based on the following candidate profile.
    Candidate Profile:
    - Skills: {resume_data.get('parsed_skills', '')}
    - Experience: {resume_data.get('parsed_experience', '')}
    - Projects: {resume_data.get('parsed_projects', '')}
    
    Return the response STRICTLY as a JSON list of strings (e.g. ["Q1", "Q2", "Q3", "Q4", "Q5"]). 
    Do not include markdown or other text.
    """
    try:
        completion = client.chat.completions.create(
            model=NVIDIA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500,
        )
        text = completion.choices[0].message.content.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        questions = json.loads(text)
        return questions[:5]
    except Exception as e:
        print(f"Error generating questions: {e}")
        return ["Could not generate questions. Please try again later."]

def evaluate_answer(question, answer):
    client = get_nvidia_client()
    
    prompt = f"""
    Evaluate the following interview answer to the question.
    Question: "{question}"
    Candidate Answer: "{answer}"
    
    You must evaluate the answer based on 5 metrics out of 100:
    1. technical_score (Accuracy and depth of technical knowledge)
    2. relevance_score (How well it answers the specific question)
    3. communication_score (Clarity and structure)
    4. grammar_score (Language proficiency)
    5. confidence_score (Inferred confidence from wording)
    
    Calculate an overall_score out of 100:
    (technical_score * 0.40) + (relevance_score * 0.20) + (communication_score * 0.15) + (grammar_score * 0.10) + (confidence_score * 0.15)
    
    Also provide a short paragraph of feedback (strengths and improvement suggestions).
    
    Return STRICTLY as a JSON object with these keys:
    "technical_score", "relevance_score", "communication_score", "grammar_score", "confidence_score", "overall_score", "feedback".
    Do not include markdown or other text.
    """
    try:
        completion = client.chat.completions.create(
            model=NVIDIA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500,
        )
        text = completion.choices[0].message.content.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        eval_data = json.loads(text)
        return eval_data
    except Exception as e:
        print(f"Error evaluating answer: {e}")
        return {
            "technical_score": 0,
            "relevance_score": 0,
            "communication_score": 0,
            "grammar_score": 0,
            "confidence_score": 0,
            "overall_score": 0,
            "feedback": f"Failed to evaluate answer: {str(e)}"
        }

def transcribe_audio_with_whisper(file_path):
    openai_key = os.environ.get("OPENAI_API_KEY")
    if not openai_key:
        print("OPENAI_API_KEY not found. Please set it in .env to use Whisper.")
        return None
        
    try:
        # Standard OpenAI client for whisper
        oai_client = OpenAI(api_key=openai_key)
        with open(file_path, "rb") as audio_file:
            transcript = oai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        return transcript.text
    except Exception as e:
        print(f"Error transcribing audio: {e}")
        return None

def chat_with_ai_stream(user_message, username="User"):
    """Stream chat with AI for interview preparation queries."""
    client = get_nvidia_client()
    
    system_prompt = f"""You are an expert AI Interview Coach assistant. The user's name is {username}. 
    You help with:
    - Interview preparation tips and strategies
    - Answering questions about common interview topics
    - Providing feedback on answers
    - Career advice and resume tips
    - Technical concept explanations
    Keep responses concise, friendly, and actionable. Use bullet points when listing things."""
    
    try:
        response = client.chat.completions.create(
            model=NVIDIA_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=500,
            stream=True
        )
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content
    except Exception as e:
        yield f"Sorry, I'm having trouble connecting right now. Please try again later. (Error: {str(e)})"
