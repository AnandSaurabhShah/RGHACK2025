from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import re
import pdfplumber
from collections import defaultdict
from typing import Dict, List, Set, Tuple

app = Flask(__name__)
CORS(app)

# -------------------------
# Resume Processing Helpers
# -------------------------

# Job roles and their required skills
JOB_ROLES = {
    "Data Scientist": ["Python", "R", "Machine Learning", "Data Analysis", "SQL", "TensorFlow", "PyTorch", "Big Data"],
    "Software Engineer": ["Python", "Java", "C++", "JavaScript", "Git", "Linux", "REST API", "CI/CD"],
    "DevOps Engineer": ["AWS", "Azure", "Docker", "Kubernetes", "Jenkins", "Ansible", "Linux", "CI/CD"],
    "Web Developer": ["JavaScript", "HTML", "CSS", "React", "Angular", "Node.js", "REST API", "Git"],
    "Machine Learning Engineer": ["Python", "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch", "SQL", "Big Data"],
    "Data Analyst": ["SQL", "Python", "Data Analysis", "Tableau", "Power BI", "R", "Big Data"],
    "Cloud Engineer": ["AWS", "Azure", "Docker", "Kubernetes", "Linux", "CI/CD", "Ansible"],
    "Full Stack Developer": ["JavaScript", "HTML", "CSS", "React", "Angular", "Node.js", "Python", "SQL", "REST API"]
}

# Escape special regex characters in skill names
def escape_regex_special_chars(skills_list: List[str]) -> List[str]:
    return [re.escape(skill) for skill in skills_list]

# Define technical skills
TECH_SKILLS = escape_regex_special_chars([
    'Python', 'Java', 'JavaScript', 'SQL', 'HTML', 'CSS', 'C++', 'C#', 'R', 
    'AWS', 'Azure', 'Docker', 'Kubernetes', 'Git', 'Linux', 'MySQL', 'MongoDB',
    'TensorFlow', 'PyTorch', 'Spark', 'Hadoop', 'React', 'Angular', 'Node.js',
    'Machine Learning', 'Deep Learning', 'Data Analysis', 'Big Data', 'CI/CD',
    'REST API', 'GraphQL', 'Tableau', 'Power BI', 'JIRA', 'Jenkins', 'Ansible', 'SVM'
])

# Scoring criteria (Total = 10 points)
CRITERIA = {
    'skills_match': {'weight': 6.0, 'max': 6.0},  # Weight for skills
    'achievements': {'weight': 2.0, 'max': 2.0},  
    'projects': {'weight': 2.0, 'max': 2.0}       
}

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from a PDF file."""
    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

def extract_sections(text: str) -> Dict[str, str]:
    """Extract sections from resume text (simplified approach)."""
    sections = {
        'skills': '',
        'achievements': '',
        'projects': ''
    }
    
    lines = text.split('\n')
    current_section = None
    
    for line in lines:
        if re.search(r'\b(skills|technologies|tools|proficiencies)\b', line, re.I):
            current_section = 'skills'
            continue
        elif re.search(r'\b(achievements|accomplishments|awards)\b', line, re.I):
            current_section = 'achievements'
            continue
        elif re.search(r'\b(projects|portfolio|work samples)\b', line, re.I):
            current_section = 'projects'
            continue
            
        if current_section:
            sections[current_section] += line + '\n'
            
    return sections

def find_skills_in_text(text: str, skills_list: List[str]) -> Set[str]:
    """Find skills in text using a safer approach."""
    found_skills = set()
    for skill in skills_list:
        original_skill = skill.replace('\\', '')
        if re.search(r'\b' + skill + r'\b', text, re.I):
            found_skills.add(original_skill)
    return found_skills

def calculate_score(text: str, sections: Dict[str, str], target_job: str, found_skills: Set[str]) -> Tuple[float, Set[str]]:
    """Calculate resume score based on skills, achievements, and projects."""
    score = 0
    required_skills = JOB_ROLES.get(target_job, [])
    
    # Skills Match (6 points)
    matched_skills = {skill for skill in required_skills if skill in found_skills}
    if len(matched_skills) > 0:
        skill_ratio = len(matched_skills) / len(required_skills)
        score += min(CRITERIA['skills_match']['max'], CRITERIA['skills_match']['weight'] * skill_ratio)
    
    # Achievements (2 points)
    achievement_indicators = [
        r'\b(achieved|award|certification|honor|recognition)\b',
        r'\b(increased|improved|reduced|optimized|enhanced)\b',
        r'\b(\d+%|\d+ percent)\b',
        r'\b\$\d+[kmb]?\b'
    ]
    
    num_achievements = sum(len(re.findall(pattern, text, re.I)) for pattern in achievement_indicators)
    score += min(CRITERIA['achievements']['max'], 0.5 * min(num_achievements, 4))
    
    # Projects (2 points)
    project_indicators = [
        r'\b(github|project|developed|created|built|implemented)\b',
        r'(https?://github\.com)',
        r'\b(app|application|system|platform|tool|dashboard)\b'
    ]
    
    num_projects = sum(len(re.findall(pattern, sections['projects'], re.I)) for pattern in project_indicators)
    technical_terms_in_projects = len(matched_skills & find_skills_in_text(sections['projects'], TECH_SKILLS))
    score += min(CRITERIA['projects']['max'], 0.5 * min(num_projects, 2) + 0.25 * min(technical_terms_in_projects, 4))
    
    return min(10, round(score, 1)), matched_skills

def generate_feedback(score: float, target_job: str, matched_skills: Set[str]) -> List[str]:
    """Generate job-specific feedback."""
    feedback = []
    required_skills = JOB_ROLES[target_job]
    
    feedback.append(f"\nScore for {target_job}: {score}/10")
    
    if score < 6:
        feedback.append("❌ Below minimum requirements")
    elif score < 8:
        feedback.append("⚠ Meets basic requirements")
    else:
        feedback.append("✅ Strong match for this role")
    
    feedback.append(f"\nMatched Skills ({len(matched_skills)}/{len(required_skills)}):")
    feedback.extend([f"- {skill}" for skill in matched_skills])
    
    missing = set(required_skills) - matched_skills
    if missing:
        feedback.append("\nMissing Skills:")
        feedback.extend([f"- {skill}" for skill in missing])
    
    return feedback

# -------------------------
# Flask Endpoints
# -------------------------

@app.route('/resume', methods=['POST'])
def resume():
    """
    Endpoint to process resume upload.
    Expects a PDF file uploaded with key 'file'.
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if not file.filename.endswith('.pdf'):
        return jsonify({"error": "Invalid file format. Please upload a PDF."}), 400

    try:
        # Save the uploaded file temporarily
        os.makedirs("uploads", exist_ok=True)
        temp_path = os.path.join("uploads", file.filename)
        file.save(temp_path)

        # Extract text from PDF
        text = extract_text_from_pdf(temp_path)

        # Extract sections from text
        sections = extract_sections(text)

        # Define job role for analysis (e.g., "Cloud Engineer")
        job_role = "Machine Learning Engineer"

        # Extract resume skills using TECH_SKILLS
        resume_skills = find_skills_in_text(text, TECH_SKILLS)

        # Calculate score (pass resume_skills as the found_skills argument)
        score, matched_skills = calculate_score(text, sections, job_role, resume_skills)

        # Generate feedback based on score and matched skills
        feedback = generate_feedback(score, job_role, matched_skills)

        # Remove the temporary file after processing
        os.remove(temp_path)

        return jsonify({"score": score, "feedback": feedback})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/analyze-resume', methods=['POST'])
def analyze_resume():
    """
    Alternate endpoint to analyze a resume.
    Expects a file with key 'resume' and an optional form field 'target_job'.
    """
    if 'resume' not in request.files:
        return jsonify({"error": "No resume file provided"}), 400

    resume_file = request.files['resume']
    target_job = request.form.get('target_job', 'Software Engineer')

    if resume_file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    try:
        temp_path = f"temp_{resume_file.filename}"
        resume_file.save(temp_path)

        text = extract_text_from_pdf(temp_path)
        sections = extract_sections(text)
        resume_skills = find_skills_in_text(text, TECH_SKILLS)
        score, matched_skills = calculate_score(text, sections, target_job, resume_skills)
        feedback = generate_feedback(score, target_job, matched_skills)

        os.remove(temp_path)

        return jsonify({
            "score": score,
            "feedback": feedback,
            "matched_skills": list(matched_skills)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------------
# Main
# -------------------------

if __name__ == '__main__':
    os.makedirs("uploads", exist_ok=True)  # Ensure upload directory exists
    app.run(debug=True)
