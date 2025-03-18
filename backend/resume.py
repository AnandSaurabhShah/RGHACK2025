"""from flask import Flask, request, jsonify
import re
import pdfplumber
from collections import defaultdict
from typing import Dict, List, Set, Tuple

app = Flask(__name__)

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

def escape_regex_special_chars(skills_list):
    return [re.escape(skill) for skill in skills_list]

TECH_SKILLS = escape_regex_special_chars([
    'Python', 'Java', 'JavaScript', 'SQL', 'HTML', 'CSS', 'C++', 'C#', 'R', 
    'AWS', 'Azure', 'Docker', 'Kubernetes', 'Git', 'Linux', 'MySQL', 'MongoDB',
    'TensorFlow', 'PyTorch', 'Spark', 'Hadoop', 'React', 'Angular', 'Node.js',
    'Machine Learning', 'Deep Learning', 'Data Analysis', 'Big Data', 'CI/CD',
    'REST API', 'GraphQL', 'Tableau', 'Power BI', 'JIRA', 'Jenkins', 'Ansible', 'SVM'
])

CRITERIA = {
    'skills_match': {'weight': 6.0, 'max': 6.0},
    'achievements': {'weight': 2.0, 'max': 2.0},
    'projects': {'weight': 2.0, 'max': 2.0}
}

def extract_text_from_pdf(pdf_path: str) -> str:
    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

def extract_sections(text: str) -> Dict[str, str]:
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
    found_skills = set()
    for skill in skills_list:
        original_skill = skill.replace('\\', '')
        if re.search(r'\b' + skill + r'\b', text, re.I):
            found_skills.add(original_skill)
    return found_skills

def calculate_score(text: str, sections: Dict[str, str], target_job: str, found_skills: Set[str]) -> Tuple[float, Set[str]]:
    score = 0
    required_skills = JOB_ROLES.get(target_job, [])
    
    matched_skills = {skill for skill in required_skills if skill in found_skills}
    if len(matched_skills) > 0:
        skill_ratio = len(matched_skills) / len(required_skills)
        score += min(CRITERIA['skills_match']['max'], CRITERIA['skills_match']['weight'] * skill_ratio)
    
    achievement_indicators = [
        r'\b(achieved|award|certification|honor|recognition)\b',
        r'\b(increased|improved|reduced|optimized|enhanced)\b',
        r'\b(\d+%|\d+ percent)\b',
        r'\b\$\d+[kmb]?\b'
    ]
    
    num_achievements = sum(len(re.findall(pattern, text, re.I)) for pattern in achievement_indicators)
    score += min(CRITERIA['achievements']['max'], 0.5 * min(num_achievements, 4))
    
    project_indicators = [
        r'\b(github|project|developed|created|built|implemented)\b',
        r'(https?://github\.com)',
        r'\b(app|application|system|platform|tool|dashboard)\b'
    ]
    
    num_projects = sum(len(re.findall(pattern, sections['projects'], re.I)) for pattern in project_indicators)
    technical_terms_in_projects = len(matched_skills & find_skills_in_text(sections['projects'], TECH_SKILLS))
    score += min(CRITERIA['projects']['max'], 0.5 * min(num_projects, 2) + 0.25 * min(technical_terms_in_projects, 4))
    
    return min(10, round(score, 1)), matched_skills

def generate_feedback(score: float, target_job: str, matched_skills: Set[str]) -> list:
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

@app.route('/analyze-resume', methods=['POST'])
def analyze_resume():
    if 'resume' not in request.files:
        return jsonify({"error": "No resume file provided"}), 400
    
    resume_file = request.files['resume']
    target_job = request.form.get('target_job', 'Software Engineer')
    
    if resume_file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    try:
        resume_path = f"temp_{resume_file.filename}"
        resume_file.save(resume_path)
        
        text = extract_text_from_pdf(resume_path)
        sections = extract_sections(text)
        resume_skills = find_skills_in_text(text, TECH_SKILLS)
        score, matched_skills = calculate_score(text, sections, target_job, resume_skills)
        feedback = generate_feedback(score, target_job, matched_skills)
        
        os.remove(resume_path)
        
        return jsonify({
            "score": score,
            "feedback": feedback,
            "matched_skills": list(matched_skills)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
"""
import re
import pdfplumber
from typing import Dict, List, Set, Tuple
from bs4 import BeautifulSoup
import markdown

def extract_text_from_pdf(pdf_path: str) -> str:
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)

def calculate_score(text: str, job_role: str) -> Tuple[float, Set[str]]:
    required_skills = {
        "Data Scientist": {"Python", "R", "Machine Learning", "Data Analysis", "SQL"},
        "Software Engineer": {"Python", "Java", "JavaScript", "Git", "Linux"},
        "DevOps Engineer": {"AWS", "Docker", "Kubernetes", "Linux", "CI/CD"},
        "Web Developer": {"JavaScript", "HTML", "CSS", "React", "Node.js"},
        "Machine Learning Engineer": {"Python", "Machine Learning", "Tensorflow", "SQL", "PyTorch"},
        "Data Analyst": {"SQL", "Python", "Data Analysis", "Tableau", "Excel"},
        "Cloud Engineer": {"AWS", "Azure", "Docker", "Linux", "Networking"},
        "Full Stack Developer": {"JavaScript", "React", "Node.js", "Python", "SQL"}
    }
    
    text_lower = text.lower()
    found_skills = {skill for skill in required_skills[job_role] if skill.lower() in text_lower}
    
    score = min(5.0, 5 * len(found_skills)/len(required_skills[job_role]))
    score += min(2.5, 0.5 * len(re.findall(r'\b(achieved|improved|optimized|award|developed)\b', text, re.I)))
    score += min(2.5, 0.5 * len(re.findall(r'\b(project|github|implemented|deployed|architected)\b', text, re.I)))
    
    return min(10, round(score, 1)), found_skills

def remove_markdown(text: str) -> str:
    html = markdown.markdown(text)
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator="\n", strip=True)

def extract_key_sections(text: str) -> Dict[str, str]:
    sections = {"experience": "", "education": "", "skills": "", "projects": ""}
    current_section = None
    
    for line in text.split("\n"):
        line_clean = line.strip()
        if not line_clean:
            continue
            
        if "experience" in line_clean.lower():
            current_section = "experience"
        elif "education" in line_clean.lower():
            current_section = "education"
        elif "skills" in line_clean.lower():
            current_section = "skills"
        elif "projects" in line_clean.lower():
            current_section = "projects"
            
        if current_section and line_clean:
            sections[current_section] += line_clean + "\n"
            
    return sections