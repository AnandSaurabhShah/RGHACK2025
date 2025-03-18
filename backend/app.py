from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import re
import pdfplumber
from typing import Dict, List, Set, Tuple
import google.generativeai as genai
import markdown
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)

# Gemini AI Configuration
GEMINI_API_KEY = "AIzaSyBFLA17NgqBiI1ejLmSq8anJ5DIbCTgksQ"
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

JOB_ROLES = {
    "Data Scientist": ["Python", "R", "Machine Learning", "Data Analysis", "SQL", "Tensorflow", "PyTorch", "Big Data"],
    "Software Engineer": ["Python", "Java", "C++", "JavaScript", "Git", "Linux", "REST API", "CI/CD"],
    "DevOps Engineer": ["AWS", "Azure", "Docker", "Kubernetes", "Jenkins", "Ansible", "Linux", "CI/CD"],
    "Web Developer": ["JavaScript", "HTML", "CSS", "React", "Angular", "Node.js", "REST API", "Git"],
    "Machine Learning Engineer": ["Python", "Machine Learning", "Deep Learning", "Tensorflow", "PyTorch", "SQL", "Big Data"],
    "Data Analyst": ["SQL", "Python", "Data Analysis", "Tableau", "Power BI", "R", "Big Data"],
    "Cloud Engineer": ["AWS", "Azure", "Docker", "Kubernetes", "Linux", "CI/CD", "Ansible"],
    "Full Stack Developer": ["JavaScript", "HTML", "CSS", "React", "Angular", "Node.js", "Python", "SQL", "REST API"]
}

def remove_markdown(text: str) -> str:
    html = markdown.markdown(text)
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator="\n", strip=True)

def better_resume(text: str, job_role: str) -> str:
    prompt = f"Enhance this resume for a {job_role} role. Add relevant skills, achievements, and projects:\n\n{text}"
    try:
        response = model.generate_content(prompt)
        return remove_markdown(response.text) if hasattr(response, 'text') else text
    except Exception as e:
        app.logger.error(f"AI Error: {str(e)}")
        return text

def extract_text_from_pdf(pdf_path: str) -> str:
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)

def calculate_score(text: str, job_role: str) -> Tuple[float, Set[str]]:
    required_skills = JOB_ROLES.get(job_role, [])
    if not required_skills:
        return 0.0, set()
    
    escaped_skills = [re.escape(skill) for skill in required_skills]
    skill_pattern = r'(?i)\b(' + '|'.join(escaped_skills) + r')\b'
    
    try:
        found_skills = set(re.findall(skill_pattern, text))
    except re.error as e:
        app.logger.error(f"Regex error: {str(e)}")
        found_skills = set()
    
    score = min(5.0, 5 * len(found_skills)/len(required_skills))
    score += min(2.5, 0.5 * len(re.findall(r'(?i)\b(achieved|improved|optimized|award)\b', text)))
    score += min(2.5, 0.5 * len(re.findall(r'(?i)\b(project|developed|implemented|github)\b', text)))
    
    return min(10, round(score, 1)), found_skills

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({"error": "Only PDF files allowed"}), 400

    try:
        os.makedirs("uploads", exist_ok=True)
        filepath = os.path.join("uploads", file.filename)
        file.save(filepath)
        
        text = extract_text_from_pdf(filepath)
        job_role = request.form.get('job_role', 'Software Engineer')
        
        if job_role not in JOB_ROLES:
            return jsonify({"error": "Invalid job role"}), 400
            
        enhanced_text = better_resume(text, job_role)
        score, skills = calculate_score(text, job_role)
        
        os.remove(filepath)
        return jsonify({
            "score": score,
            "enhanced": enhanced_text,
            "skills": list(skills),
            "job_role": job_role,
            "original": text[:2000] + "..." if len(text) > 2000 else text
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'filepath' in locals() and os.path.exists(filepath):
            os.remove(filepath)

@app.route('/chat', methods=['POST'])
def chat_with_pdf():
    data = request.get_json()
    text = data.get('text', '')
    message = data.get('message', '')
    
    if not text or not message:
        return jsonify({"error": "Missing text or message"}), 400
    
    try:
        prompt = f"""Analyze this resume and answer the question. Follow these rules:
        1. Be specific to the resume content
        2. Keep responses under 200 words
        3. Highlight key details from the resume
        4. If unsure, ask for clarification
        
        Resume Content: {text[:15000]}
        Question: {message}
        Answer:"""
        
        response = model.generate_content(prompt)
        return jsonify({
            "response": remove_markdown(response.text) if hasattr(response, 'text') else "No response generated"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)