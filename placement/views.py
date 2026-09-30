import re
import pypdf
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Count, Avg, Q
from django.db import transaction
from .models import InterviewExperience, ResumeAnalysis, Company, JobProfile
from .utils import is_spam_experience, create_linkedin_badge


# ==========================================
# 🛠️ HELPER FUNCTIONS
# ==========================================
def normalize_company_name(name):
    if not name:
        return ""
    
    name_clean = name.strip()
    name_lower = name_clean.lower()
    
    alias_mapping = {
        'tcs': 'TCS',
        'tata consultancy services': 'TCS',
        'tcs (tata consultancy services)': 'TCS',
        'infosys': 'Infosys',
        'infosys limited': 'Infosys',
        'infy': 'Infosys',
        'wipro': 'Wipro',
        'wipro limited': 'Wipro',
        'cognizant': 'Cognizant',
        'cognizant technology solutions': 'Cognizant',
        'cts': 'Cognizant',
        'accenture': 'Accenture',
        'accenture india': 'Accenture',
        'amazon': 'Amazon',
        'amazon india': 'Amazon',
        'microsoft': 'Microsoft',
        'google': 'Google',
    }
    
    if name_lower in alias_mapping:
        return alias_mapping[name_lower]
    
    return name_clean.title() if (name_clean.islower() or name_clean.isupper()) else name_clean


def clean_text_and_math(text):
    if not text:
        return "No response recorded."
    
    cleaned = str(text).strip().strip('"\'').strip()
    if cleaned.startswith('""') and cleaned.endswith('""'):
        cleaned = cleaned[2:-2]
    
    cleaned = re.sub(r'\$([^$]+)\$', r'\1', cleaned)
    return cleaned


# ==========================================
# 🏠 HOME PAGE VIEW
# ==========================================
def home(request):
    total_reviews = InterviewExperience.objects.filter(is_spam=False).count()
    total_companies = InterviewExperience.objects.filter(is_spam=False).values('company_name').distinct().count()
    return render(request, 'placement/home.html', {
        'total_reviews': total_reviews,
        'total_companies': total_companies
    })


# ==========================================
# 🔐 AUTHENTICATION VIEWS
# ==========================================
@transaction.atomic
def register_user(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not username or not email or not password:
            messages.error(request, "All fields are required!")
            return render(request, 'placement/register.html')

        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return render(request, 'placement/register.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username is already taken!")
            return render(request, 'placement/register.html')

        user = User.objects.create_user(username=username, email=email, password=password)
        login(request, user)
        messages.success(request, f"Welcome {username}! Your account was created successfully.")
        return redirect('dashboard')

    return render(request, 'placement/register.html')


def login_user(request):
    user_type = request.GET.get('type', request.POST.get('user_type', 'student'))

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()

            if user_type == 'admin':
                if user.is_staff or user.is_superuser:
                    login(request, user)
                    return redirect('/admin/')
                else:
                    messages.error(request, "Access Denied: You do not have Admin permissions!")
                    return render(request, 'placement/login.html', {'form': form, 'user_type': user_type})
            else:
                login(request, user)
                return redirect('dashboard')
        else:
            messages.error(request, "Invalid username or password!")
    else:
        form = AuthenticationForm()

    return render(request, 'placement/login.html', {'form': form, 'user_type': user_type})


def logout_user(request):
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect('home')


# ==========================================
# 📊 USER ANALYTICS DASHBOARD
# ==========================================
@login_required(login_url='login')
def dashboard(request):
    user_experiences = InterviewExperience.objects.filter(user=request.user).order_by('-created_at')
    user_analyses = ResumeAnalysis.objects.filter(user=request.user).order_by('-created_at')
    
    avg_score = user_analyses.aggregate(Avg('match_score'))['match_score__avg'] or 0

    return render(request, 'placement/dashboard.html', {
        'experiences': user_experiences,
        'analyses': user_analyses,
        'total_shared': user_experiences.count(),
        'avg_score': round(avg_score, 1),
    })


# ==========================================
# 📝 EXPERIENCES VIEW
# ==========================================
def experiences(request):
    difficulty_filter = request.GET.get('difficulty', '')
    all_exps = InterviewExperience.objects.filter(is_spam=False).select_related('user', 'company').order_by('-created_at')

    if difficulty_filter:
        all_exps = all_exps.filter(difficulty=difficulty_filter)

    return render(request, 'placement/experiences.html', {
        'experiences': all_exps,
        'selected_difficulty': difficulty_filter
    })


# ==========================================
# 🏢 COMPANY DETAIL VIEW
# ==========================================
def company_detail(request, company_name):
    standard_name = normalize_company_name(company_name)

    all_company_exps = InterviewExperience.objects.filter(
        Q(company_name__iexact=standard_name) | Q(company_name__iexact=company_name),
        is_spam=False
    ).select_related('user').order_by('-created_at')
    
    cleared_count = all_company_exps.filter(outcome='Cleared').count()
    not_cleared_count = all_company_exps.filter(outcome='Not Cleared').count()
    total_decided = cleared_count + not_cleared_count

    success_rate = round((cleared_count / total_decided) * 100) if total_decided > 0 else None

    elimination_stats = all_company_exps.exclude(elimination_round__iexact='None')\
        .exclude(elimination_round__exact='')\
        .values('elimination_round')\
        .annotate(count=Count('elimination_round'))\
        .order_by('-count')

    selected_round = request.GET.get('round', '')
    experiences_list = all_company_exps
    if selected_round:
        experiences_list = experiences_list.filter(
            Q(elimination_round__iexact=selected_round) | 
            Q(elimination_round__iexact='None') | 
            Q(elimination_round__isnull=True) |
            Q(elimination_round__exact='')
        )

    round_tips = {
        'Round 1': "Round 1 usually tests Aptitude, Reasoning, and Basic Coding Speed. Practice mock tests on IndiaBIX and solve LeetCode Easy problems within time limits.",
        'Round 2': "Round 2 is typically the primary elimination round for Technical DSA & Core CS. Focus on Trees, Graphs, Dynamic Programming, and explain your code clearly out loud.",
        'Round 3': "Round 3 focuses on Advanced Coding, System Design, or Core CS Concepts (OS, DBMS, Computer Networks). Prepare to explain architecture decisions and database design.",
        'HR': "The HR/Behavioral round evaluates your communication and cultural fit. Practice answering using the STAR method (Situation, Task, Action, Result) and prepare well on your resume projects."
    }

    context = {
        'company_name': standard_name,
        'experiences': experiences_list,
        'total_count': all_company_exps.count(),
        'success_rate': success_rate,
        'elimination_stats': elimination_stats,
        'selected_round': selected_round,
        'current_tip': round_tips.get(selected_round, "")
    }
    return render(request, 'placement/company_detail.html', context)


# ==========================================
# ✍️ SHARE EXPERIENCE VIEW
# ==========================================
@login_required(login_url='login')
@transaction.atomic
def share_experience(request):
    if request.method == 'POST':
        raw_company_name = request.POST.get('company_name', '')
        company_name = normalize_company_name(raw_company_name)
        
        experience_text = request.POST.get('experience', '')
        questions_text = request.POST.get('questions_asked', '')
        
        is_spam, spam_reason = is_spam_experience(f"{experience_text} {questions_text}")
        if is_spam:
            messages.error(request, f"Submission rejected: {spam_reason}")
            return render(request, 'placement/share_experience.html')

        resume_file = request.FILES.get('resume_file')
        company_obj = Company.objects.filter(name__iexact=company_name).first()

        new_experience = InterviewExperience.objects.create(
            user=request.user,
            company=company_obj,
            company_name=company_name,
            role=request.POST.get('role', '').strip(),
            difficulty=request.POST.get('difficulty'),
            outcome=request.POST.get('outcome'),
            elimination_round=request.POST.get('elimination_round'),
            experience=experience_text,
            questions_asked=questions_text,
            tips=request.POST.get('tips', ''),
            resume_file=resume_file,
            is_spam=False
        )
        
        badge_rel_path = create_linkedin_badge(request.user.username, company_name)
        new_experience.generated_badge = badge_rel_path
        new_experience.save()

        messages.success(request, "Experience shared successfully! Here is your shareable LinkedIn graphic.")
        return redirect('linkedin_badge', exp_id=new_experience.id)

    return render(request, 'placement/share_experience.html')


# ==========================================
# 🎨 LINKEDIN BADGE VIEWS
# ==========================================
def linkedin_badge(request, exp_id):
    experience = get_object_or_404(InterviewExperience, id=exp_id)
    return render(request, 'placement/linkedin_badge.html', {'exp': experience})


@login_required(login_url='login')
def user_badges(request):
    latest_exp = InterviewExperience.objects.filter(user=request.user).order_by('-created_at').first()
    if latest_exp:
        return render(request, 'placement/linkedin_badge.html', {'exp': latest_exp})
    
    messages.warning(request, "Please share an interview experience first to view your badge.")
    return redirect('share_experience')


# ==========================================
# 🏢 COMPANIES LIST VIEW
# ==========================================
def companies(request):
    raw_names = InterviewExperience.objects.filter(is_spam=False).values_list('company_name', flat=True).distinct()
    normalized_names = sorted(list(set(normalize_company_name(name) for name in raw_names if name)))
    return render(request, 'placement/companies.html', {'company_names': normalized_names})


# ==========================================
# 📄 RESUME ANALYZER VIEW
# ==========================================
@login_required(login_url='login')
@transaction.atomic
def resume_analyzer(request):
    result = None
    recommended_roles = []
    job_profiles = JobProfile.objects.all()

    if request.method == 'POST':
        job_profile_id = request.POST.get('job_profile_id')
        selected_profile = None

        if job_profile_id:
            selected_profile = JobProfile.objects.filter(id=job_profile_id).first()

        if selected_profile:
            company_name = normalize_company_name(selected_profile.company_name)
            role = selected_profile.role_title
        else:
            raw_company_name = request.POST.get('company_name', '')
            company_name = normalize_company_name(raw_company_name)
            role = request.POST.get('role', '').strip()

        extracted_text = ""
        if 'resume_pdf' in request.FILES:
            try:
                pdf_file = request.FILES['resume_pdf']
                reader = pypdf.PdfReader(pdf_file)
                for page in reader.pages:
                    extracted_text += (page.extract_text() or "") + " "
            except Exception:
                messages.warning(request, "Unable to fully extract PDF text. Analysis proceeds using manual inputs.")

        user_skills_raw = request.POST.get('skills', '')
        user_projects_raw = request.POST.get('projects', '')
        full_resume_content = (user_skills_raw + " " + user_projects_raw + " " + extracted_text).lower()

        # Dynamic target skills check from selected Job Profile or entered skills
        if selected_profile and selected_profile.required_skills:
            target_skills = [s.strip().lower() for s in selected_profile.required_skills.split(',') if s.strip()]
        elif user_skills_raw:
            target_skills = [s.strip().lower() for s in user_skills_raw.split(',') if s.strip()]
        else:
            target_skills = ['python', 'java', 'dsa', 'sql', 'django', 'react', 'git', 'system design']

        # Word-boundary sub-matching to prevent partial string matching errors
        matched_skills = []
        for k in target_skills:
            pattern = r'\b' + re.escape(k) + r'\b'
            if re.search(pattern, full_resume_content):
                matched_skills.append(k)

        cleared_experiences = InterviewExperience.objects.filter(
            Q(company_name__iexact=company_name),
            outcome='Cleared',
            is_spam=False
        )

        senior_text = ""
        for exp in cleared_experiences:
            senior_text += f" {exp.questions_asked} {exp.experience} {exp.tips}"
        senior_text = senior_text.lower()

        senior_skills = [k for k in target_skills if re.search(r'\b' + re.escape(k) + r'\b', senior_text)]
        missing_senior_skills = list(set(senior_skills) - set(matched_skills))

        base_score = 40 + (len(matched_skills) * 6 if target_skills else 0)

        if cleared_experiences.count() > 0:
            if len(missing_senior_skills) == 0 and len(senior_skills) > 0:
                base_score += 15
            else:
                base_score -= (len(missing_senior_skills) * 3)
        else:
            if len(matched_skills) >= 3:
                base_score += 10

        if len(user_projects_raw.strip()) > 100 or len(extracted_text) > 200:
            base_score += 10

        score = max(30, min(base_score, 98))

        missing_recommendations = []
        if 'dsa' not in matched_skills and 'algorithms' not in full_resume_content:
            missing_recommendations.append("Strengthen Data Structures & Algorithms (LeetCode / HackerRank)")

        if 'sql' not in matched_skills and 'dbms' not in matched_skills:
            missing_recommendations.append("Include Relational Database concepts (SQL, DBMS, Schema Design)")

        missing_skills_list = [s for s in target_skills if s not in matched_skills]
        for missing_skill in missing_skills_list[:6]:
            missing_recommendations.append(
                f"Add proven experience in '{missing_skill.upper()}' — required for {role} at {company_name}"
            )

        project_boosters = []
        if len(user_projects_raw.strip()) < 120 and len(extracted_text) < 150:
            project_boosters.append("Add at least 2 End-to-End Capstone projects with live GitHub repository links")

        hackathon_suggestions = []
        if score < 75:
            hackathon_suggestions.append("Compete in Smart India Hackathon (SIH) or Devfolio Hackathons to build portfolio strength")

        if score >= 80:
            verdict = "EXCELLENT PROFILE MATCH"
            status_color = "#10b981"
            insight_text = f"Your resume aligns strongly with candidates who cleared interview rounds at {company_name}."
        elif score >= 60:
            verdict = "MODERATE MATCH (Profile Upgrade Recommended)"
            status_color = "#f59e0b"
            insight_text = f"Your resume hits core basics, but lacks key domain skills frequently expected by {company_name} recruiters."
        else:
            verdict = "HIGH REJECTION RISK"
            status_color = "#ef4444"
            insight_text = f"Your resume lacks essential core skills required to pass initial screening rounds at {company_name}."

        result = {
            'company_name': company_name,
            'role': role,
            'score': score,
            'verdict': verdict,
            'status_color': status_color,
            'insight_text': insight_text,
            'matched_skills': [s.upper() for s in matched_skills],
            'missing_recommendations': missing_recommendations,
            'project_boosters': project_boosters,
            'hackathon_suggestions': hackathon_suggestions,
            'cleared_seniors_count': cleared_experiences.count()
        }

        # -----------------------------------------------------------------
        # 🎯 CROSS-MATCH GENERAL ROLES ACROSS OTHER COMPANIES (> 50% MATCH)
        # -----------------------------------------------------------------
        ALL_KNOWN_SKILLS = [
            'python', 'java', 'c++', 'c', 'c#', 'dsa', 'sql', 'django', 'react', 
            'aws', 'cloud', 'data analysis', 'html', 'css', 'javascript', 'dbms',
            'node', 'express', 'mongodb', 'git', 'docker', 'machine learning', 'ai'
        ]
        all_extracted_resume_skills = [
            s for s in ALL_KNOWN_SKILLS if re.search(r'\b' + re.escape(s) + r'\b', full_resume_content)
        ]

        if job_profiles.exists():
            for prof in job_profiles:
                if selected_profile and prof.id == selected_profile.id:
                    continue
                if prof.company_name.lower() == company_name.lower() and prof.role_title.lower() == role.lower():
                    continue

                if not prof.required_skills:
                    continue

                req_skills = [s.strip().lower() for s in prof.required_skills.split(',') if s.strip()]
                if not req_skills:
                    continue

                found_skills = [
                    s for s in req_skills 
                    if re.search(r'\b' + re.escape(s) + r'\b', full_resume_content) or s in all_extracted_resume_skills
                ]
                role_match_percentage = round((len(found_skills) / len(req_skills)) * 100)

                if role_match_percentage >= 50:
                    recommended_roles.append({
                        'company_name': prof.company_name,
                        'role_title': prof.role_title,
                        'match_score': role_match_percentage,
                        'matched_skills': [s.upper() for s in found_skills],
                        'missing_skills': [s.upper() for s in req_skills if s not in found_skills][:5]
                    })
        else:
            default_profiles = [
                {'company_name': 'TCS', 'role_title': 'Cloud Engineer', 'required_skills': ['aws', 'cloud', 'python', 'sql']},
                {'company_name': 'Wipro', 'role_title': 'Data Analyst', 'required_skills': ['sql', 'python', 'data analysis']},
                {'company_name': 'Infosys', 'role_title': 'Full Stack Developer', 'required_skills': ['django', 'react', 'python', 'html']},
            ]
            for prof in default_profiles:
                p_company = prof['company_name']
                p_role = prof['role_title']
                
                if p_company.lower() == company_name.lower() and p_role.lower() == role.lower():
                    continue

                req_skills = prof['required_skills']
                found_skills = [
                    s for s in req_skills if re.search(r'\b' + re.escape(s) + r'\b', full_resume_content)
                ]
                role_match_percentage = round((len(found_skills) / len(req_skills)) * 100)

                if role_match_percentage >= 50:
                    recommended_roles.append({
                        'company_name': p_company,
                        'role_title': p_role,
                        'match_score': role_match_percentage,
                        'matched_skills': [s.upper() for s in found_skills],
                        'missing_skills': [s.upper() for s in req_skills if s not in found_skills][:5]
                    })

        recommended_roles.sort(key=lambda x: x['match_score'], reverse=True)

        ResumeAnalysis.objects.create(
            user=request.user,
            company_name=company_name,
            role=role,
            skills=", ".join(matched_skills) if matched_skills else "None Detected",
            projects=user_projects_raw[:200] if user_projects_raw else "Uploaded via PDF",
            match_score=score
        )

    return render(request, 'placement/resume_analyzer.html', {
        'result': result,
        'recommended_roles': recommended_roles,
        'job_profiles': job_profiles
    })


# ==========================================
# 🎯 CGPA & ARREARS ELIGIBILITY CHECKER
# ==========================================
def check_eligibility(request):
    companies = Company.objects.all()
    
    if request.method == 'POST':
        company_id = request.POST.get('company_id')
        student_cgpa = float(request.POST.get('cgpa', 0.0))
        active_arrears = int(request.POST.get('active_arrears', 0))
        history_arrears = int(request.POST.get('history_arrears', 0))

        company = get_object_or_404(Company, id=company_id)
        
        is_eligible = True
        reasons = []

        if student_cgpa < company.min_cgpa:
            is_eligible = False
            reasons.append(f"Your CGPA ({student_cgpa}) is below the required minimum ({company.min_cgpa}).")

        if active_arrears > company.max_active_arrears:
            is_eligible = False
            reasons.append(f"Your active arrears ({active_arrears}) exceed the allowed limit ({company.max_active_arrears}).")

        if history_arrears > company.max_history_arrears:
            is_eligible = False
            reasons.append(f"Your history of arrears ({history_arrears}) exceeds the allowed limit ({company.max_history_arrears}).")

        return render(request, 'placement/eligibility_result.html', {
            'company': company,
            'is_eligible': is_eligible,
            'reasons': reasons
        })

    return render(request, 'placement/eligibility_form.html', {'companies': companies})


# ==========================================
# 🤖 INTERACTIVE MOCK INTERVIEW ENGINE
# ==========================================
@login_required(login_url='login')
def start_mock_interview(request, company_name):
    standard_name = normalize_company_name(company_name)
    experiences = InterviewExperience.objects.filter(
        Q(company_name__iexact=standard_name) | Q(company_name__iexact=company_name),
        outcome='Cleared',
        is_spam=False
    )
    
    questions = []
    for exp in experiences:
        if exp.questions_asked:
            q_list = [q.strip() for q in exp.questions_asked.split('\n') if len(q.strip()) > 5]
            questions.extend(q_list)
            
    if not questions:
        questions = [
            "Binary Tree Zigzag Level Order Traversal",
            "Minimum number of platforms required for a train station",
            "Explain DBMS ACID properties and indexing",
            "How do you handle conflict or tight deadlines when working in a development team?",
            "Explain a challenging project you worked on and how you solved key technical obstacles."
        ]

    unique_questions = list(dict.fromkeys(questions))[:5]

    if request.method == 'POST':
        results = []
        numeric_scores = []
        weak_topics = []

        for index, q in enumerate(unique_questions):
            ans = request.POST.get(f'answer_{index}', request.POST.get(f'question_{index}', '')).strip()
            cleaned_ans = clean_text_and_math(ans)
            word_count = len(cleaned_ans.split()) if cleaned_ans and cleaned_ans != "No response recorded." else 0
            
            if word_count > 30:
                score = "Strong Answer"
                status = "#10b981"
                numeric_scores.append(100)
            elif word_count > 10:
                score = "Partial Answer"
                status = "#3b82f6"
                numeric_scores.append(70)
            elif word_count > 0:
                score = "Needs Depth"
                status = "#f59e0b"
                numeric_scores.append(40)
                weak_topics.append({
                    'name': f"Q{index + 1}",
                    'recommendation': "Expand technical explanations with time complexity and core principles."
                })
            else:
                score = "Skipped"
                status = "#ef4444"
                numeric_scores.append(0)
                weak_topics.append({
                    'name': f"Q{index + 1}",
                    'recommendation': "Not attempted. Practice core concepts for this topic."
                })

            results.append({
                'question': q,
                'answer': cleaned_ans,
                'score': score,
                'status': status
            })

        score_percentage = sum(numeric_scores) / len(numeric_scores) if numeric_scores else 0

        return render(request, 'placement/mock_interview_result.html', {
            'company_name': standard_name,
            'results': results,
            'score_percentage': round(score_percentage, 1),
            'weak_topics': weak_topics,
            'first_attempt': True
        })

    return render(request, 'placement/mock_interview.html', {
        'company_name': standard_name,
        'questions': unique_questions
    })