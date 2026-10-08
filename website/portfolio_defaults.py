"""
Canonical portfolio data definitions and fallback providers for Daniel John Britto.
Used by:
- Django data migrations (auto-populating new production databases on deploy)
- Management commands (seed_data)
- View fallback handlers (ensures zero empty sections if DB is unseeded or unreachable)
"""

DEFAULT_PROFILE = {
    "full_name": "Daniel John Britto",
    "title": "Python Developer | Django & Full Stack Developer",
    "headline": "Python Developer at M7 Technology | Specializing in Django Backend & Full Stack Development",
    "bio": "Python Developer currently working at M7 Technology. Experienced in developing backend services, RESTful APIs, and database-driven web solutions using Python, Django, Flask, and PostgreSQL. Previously worked at Levantare Technology.",
    "years_of_experience": 1,
    "projects_completed": 8,
    "location": "Chennai, India",
    "email": "danieljohnbrittoaj@gmail.com",
    "phone": "+91 9345655206",
    "resume_url": "#",
    "profile_image_url": "/static/images/profile.svg",
    "is_active": True,
}

DEFAULT_SOCIAL_LINKS = [
    {"platform": "GitHub", "url": "https://github.com/danieljohnbritto21", "icon_name": "github", "order": 1},
    {"platform": "LinkedIn", "url": "https://www.linkedin.com/in/daniel-john-britto-21-dev", "icon_name": "linkedin", "order": 2},
    {"platform": "Email", "url": "mailto:danieljohnbrittoaj@gmail.com", "icon_name": "mail", "order": 3},
]

DEFAULT_SKILLS = [
    # Languages
    {"name": "Python", "category": "Languages", "proficiency": 92, "icon_name": "python", "order": 1},
    {"name": "TypeScript / JS", "category": "Languages", "proficiency": 84, "icon_name": "javascript", "order": 2},
    {"name": "HTML5", "category": "Languages", "proficiency": 90, "icon_name": "html", "order": 3},
    {"name": "CSS3", "category": "Languages", "proficiency": 88, "icon_name": "css", "order": 4},
    {"name": "C#", "category": "Languages", "proficiency": 72, "icon_name": "code", "order": 5},

    # Frameworks
    {"name": "Django", "category": "Frameworks", "proficiency": 90, "icon_name": "django", "order": 1},
    {"name": "Angular", "category": "Frameworks", "proficiency": 85, "icon_name": "angular", "order": 2},
    {"name": "Flask", "category": "Frameworks", "proficiency": 80, "icon_name": "flask", "order": 3},
    {"name": "Node.js", "category": "Frameworks", "proficiency": 70, "icon_name": "node", "order": 4},

    # Databases
    {"name": "PostgreSQL", "category": "Databases", "proficiency": 88, "icon_name": "postgresql", "order": 1},
    {"name": "MySQL", "category": "Databases", "proficiency": 90, "icon_name": "mysql", "order": 2},
    {"name": "SQLite", "category": "Databases", "proficiency": 88, "icon_name": "database", "order": 3},

    # Tools
    {"name": "Git", "category": "Tools", "proficiency": 90, "icon_name": "git", "order": 1},
    {"name": "GitHub", "category": "Tools", "proficiency": 92, "icon_name": "github", "order": 2},
    {"name": "Postman", "category": "Tools", "proficiency": 88, "icon_name": "api", "order": 3},
    {"name": "VS Code", "category": "Tools", "proficiency": 95, "icon_name": "vscode", "order": 4},
]

DEFAULT_EXPERIENCES = [
    {
        "company": "M7 Technology",
        "role": "Python Developer",
        "location": "India",
        "is_current": True,
        "start_date": "Present",
        "end_date": "Present",
        "description": "Serving as a Python Developer at M7 Technology.",
        "responsibilities_raw": "Developing and maintaining scalable Python backend services\nBuilding and optimizing RESTful APIs for web applications\nCollaborating on system architecture and code reviews\nEnsuring performance, data security, and database query optimization",
        "tech_stack": "Python, Django, PostgreSQL, REST APIs, Git",
        "order": 1,
    },
    {
        "company": "Levantare Technology",
        "role": "Software Developer",
        "location": "Chennai, India",
        "is_current": False,
        "start_date": "Jan 2026",
        "end_date": "2026",
        "description": "Developed and maintained backend services using Flask, building RESTful APIs, and managing PostgreSQL databases.",
        "responsibilities_raw": "Developing and maintaining backend services using Flask\nWorking on robust REST API integrations across services\nFixing user interface (UI) issues in Angular\nDebugging browser console errors and inspecting backend server logs\nValidating data integrity using PostgreSQL and pgAdmin",
        "tech_stack": "Python, Flask, PostgreSQL, REST APIs, Angular, Git",
        "order": 2,
    },
    {
        "company": "Besant Technologies",
        "role": "Full Stack Python Trainee",
        "location": "Chennai, India",
        "is_current": False,
        "start_date": "Nov 2024",
        "end_date": "Apr 2025",
        "description": "Completed an intensive full-stack Python development training program covering OOP, SQL database design, and web applications.",
        "responsibilities_raw": "Hands-on training in Python programming and Object-Oriented Programming (OOP)\nSQL database design, queries, and integration using MySQL Workbench\nFull-stack web development principles and CRUD application architecture\nVersion control workflows using Git and GitHub",
        "tech_stack": "Python, MySQL, SQL, Git, GitHub",
        "order": 3,
    },
]

DEFAULT_PROJECTS = [
    {
        "title": "Phishing Detection using XGBoost",
        "summary": "Intelligent machine learning cybersecurity system analyzing URL structure and DOM features to identify malicious phishing sites with 98.4% accuracy.",
        "description": "Built using Python, Scikit-Learn, XGBoost, and Django. Features a real-time URL classification engine that inspects lexical traits, SSL domain age, and page scripts.",
        "image_url": "/static/images/project-placeholder.svg",
        "tech_stack": "Python, Machine Learning, XGBoost, Django, Scikit-Learn",
        "features_raw": "98.4% detection accuracy on benchmark datasets\nReal-time URL feature extraction pipeline\nRESTful API integration for instant URL validation",
        "github_url": "https://github.com/danieljohnbritto21",
        "live_url": "",
        "is_featured": True,
        "order": 1,
    },
    {
        "title": "Blockchain E-Voting with Face Recognition",
        "summary": "Tamper-proof biometric voting portal combining immutable SHA-256 blockchain ledger technology with real-time OpenCV facial identification.",
        "description": "Designed to guarantee election integrity. Voter identity is verified via facial recognition before block creation and cryptographic vote casting.",
        "image_url": "/static/images/project-placeholder.svg",
        "tech_stack": "Python, Blockchain, OpenCV, Django, Cryptography",
        "features_raw": "Biometric face authentication before voting access\nSHA-256 immutable block structure\nAutomatic vote tallies with cryptographic verification",
        "github_url": "https://github.com/danieljohnbritto21",
        "live_url": "",
        "is_featured": True,
        "order": 2,
    },
    {
        "title": "Inventory Management System",
        "summary": "Enterprise stock control platform with real-time inventory tracking, low-stock warnings, purchase order management, and analytics.",
        "description": "Full-stack Django application using PostgreSQL. Features automated email alerts when stock dips below threshold and dynamic chart reporting.",
        "image_url": "/static/images/project-placeholder.svg",
        "tech_stack": "Python, Django, PostgreSQL, Angular, JavaScript",
        "features_raw": "Automated low-stock trigger notifications\nSupplier directory and purchase order workflows\nReal-time stock movement reporting graphs",
        "github_url": "https://github.com/danieljohnbritto21",
        "live_url": "",
        "is_featured": True,
        "order": 3,
    },
    {
        "title": "Weather Forecast App",
        "summary": "Dynamic weather forecasting web application offering live location updates, 5-day forecasts, and interactive weather maps.",
        "description": "Built using Python Django and OpenWeather REST API. Features responsive UI themes that adapt to current weather conditions.",
        "image_url": "/static/images/project-placeholder.svg",
        "tech_stack": "Python, Django, REST API, OpenWeather API, CSS3",
        "features_raw": "Live location-based weather fetching\n5-day hourly temperature and humidity forecasts\nResponsive adaptive visual themes",
        "github_url": "https://github.com/danieljohnbritto21",
        "live_url": "",
        "is_featured": True,
        "order": 4,
    },
    {
        "title": "School Management System",
        "summary": "Comprehensive academic portal managing student records, daily attendance, teacher schedules, gradebooks, and fee tracking.",
        "description": "Django web application utilizing MySQL. Includes granular role-based permissions for administrators, faculty, students, and parents.",
        "image_url": "/static/images/project-placeholder.svg",
        "tech_stack": "Python, Django, MySQL, Angular, CSS3",
        "features_raw": "Multi-role permission system (Admin, Staff, Student)\nAutomated gradebook computation & report cards\nFee receipt generation and payment status logs",
        "github_url": "https://github.com/danieljohnbritto21",
        "live_url": "",
        "is_featured": True,
        "order": 5,
    },
    {
        "title": "Todo App (Django)",
        "summary": "Modern task management system with priority tagging, category filtering, deadline notifications, and seamless AJAX updates.",
        "description": "Built with Django and Vanilla JS. Features custom CSS glassmorphism styling and instantaneous status updates without page reloads.",
        "image_url": "/static/images/project-placeholder.svg",
        "tech_stack": "Python, Django, SQLite, Vanilla JS, CSS3",
        "features_raw": "Priority classification & deadline tracking\nAJAX-powered instant complete/delete actions\nClean glassmorphic user dashboard",
        "github_url": "https://github.com/danieljohnbritto21",
        "live_url": "",
        "is_featured": True,
        "order": 6,
    },
    {
        "title": "Employee Management System",
        "summary": "Centralized HR management platform handling employee onboarding, department hierarchies, leave requests, and payroll records.",
        "description": "Engineered using Django and PostgreSQL. Features interactive department analytics and employee performance evaluation modules.",
        "image_url": "/static/images/project-placeholder.svg",
        "tech_stack": "Python, Django, PostgreSQL, Angular",
        "features_raw": "Complete employee profile lifecycle management\nLeave request approval workflow for managers\nSalary structure breakdowns and HR charts",
        "github_url": "https://github.com/danieljohnbritto21",
        "live_url": "",
        "is_featured": True,
        "order": 7,
    },
    {
        "title": "Task Priority Manager",
        "summary": "Agile task scheduling application applying the Eisenhower Matrix framework for urgent vs. important task organization.",
        "description": "Developed using Python Django and SQLite. Helps developers and teams streamline workflow prioritization and track time metrics.",
        "image_url": "/static/images/project-placeholder.svg",
        "tech_stack": "Python, Django, SQLite, Angular",
        "features_raw": "4-quadrant Eisenhower Matrix categorization\nDrag-and-drop task prioritization\nTime spent tracking and efficiency stats",
        "github_url": "https://github.com/danieljohnbritto21",
        "live_url": "",
        "is_featured": True,
        "order": 8,
    },
]

DEFAULT_EDUCATION = [
    {
        "degree": "Bachelor of Engineering (B.E.) - Computer Science / IT",
        "institution": "Anna University Affiliated Engineering College",
        "score": "8.2 CGPA",
        "location": "Chennai, Tamil Nadu",
        "start_year": "2020",
        "end_year": "2024",
        "order": 1,
    },
    {
        "degree": "Higher Secondary Certificate (HSC) - Computer Science",
        "institution": "State Board High School",
        "score": "88%",
        "location": "Chennai, Tamil Nadu",
        "start_year": "2018",
        "end_year": "2020",
        "order": 2,
    },
]

DEFAULT_CERTIFICATES = [
    {
        "title": "Python & Django Backend Certification",
        "issuer": "Full Stack Developer Program",
        "issue_date": "2024",
        "credential_url": "https://example.com/cert/python",
        "image_url": "/static/images/certificate-placeholder.svg",
        "order": 1,
    },
    {
        "title": "Angular & Frontend Web Engineering",
        "issuer": "Full Stack Developer Program",
        "issue_date": "2024",
        "credential_url": "https://example.com/cert/angular",
        "image_url": "/static/images/certificate-placeholder.svg",
        "order": 2,
    },
]


class FallbackItem:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class FallbackExperience(FallbackItem):
    def responsibilities_list(self):
        raw = getattr(self, "responsibilities_raw", "")
        if not raw:
            return []
        return [line.strip().lstrip("•- ") for line in raw.splitlines() if line.strip()]


class FallbackProject(FallbackItem):
    def tech_list(self):
        raw = getattr(self, "tech_stack", "")
        if not raw:
            return []
        return [t.strip() for t in raw.split(",") if t.strip()]

    def features_list(self):
        raw = getattr(self, "features_raw", "")
        if not raw:
            return []
        return [f.strip().lstrip("•- ") for f in raw.splitlines() if f.strip()]


def get_fallback_context_data():
    """Returns fallback dictionaries and objects if database is unseeded or unreachable."""
    profile = FallbackItem(**DEFAULT_PROFILE)
    social_links = [FallbackItem(**s) for s in DEFAULT_SOCIAL_LINKS]
    skills = [FallbackItem(**s) for s in DEFAULT_SKILLS]
    
    skills_by_category = {
        "Languages": [s for s in skills if s.category == "Languages"],
        "Frameworks": [s for s in skills if s.category == "Frameworks"],
        "Databases": [s for s in skills if s.category == "Databases"],
        "Tools": [s for s in skills if s.category == "Tools"],
    }
    
    experiences = [FallbackExperience(**e) for e in DEFAULT_EXPERIENCES]
    projects = [FallbackProject(**p) for p in DEFAULT_PROJECTS]
    education_list = [FallbackItem(**ed) for ed in DEFAULT_EDUCATION]
    certificates = [FallbackItem(**c) for c in DEFAULT_CERTIFICATES]

    return {
        "profile": profile,
        "social_links": social_links,
        "skills": skills,
        "skills_by_category": skills_by_category,
        "experiences": experiences,
        "projects": projects,
        "education_list": education_list,
        "certificates": certificates,
    }


def seed_database_tables(apps=None, force=False):
    """
    Seeds database tables with canonical portfolio data.
    Can be used from migrations (passing apps) or directly.
    If force=True, existing rows are deleted and freshly recreated.
    """
    if apps:
        Profile = apps.get_model("website", "Profile")
        SocialLink = apps.get_model("website", "SocialLink")
        Skill = apps.get_model("website", "Skill")
        Experience = apps.get_model("website", "Experience")
        Project = apps.get_model("website", "Project")
        Education = apps.get_model("website", "Education")
        Certificate = apps.get_model("website", "Certificate")
    else:
        from website.models import (
            Profile, SocialLink, Skill, Experience, Project, Education, Certificate
        )

    if force:
        Profile.objects.all().delete()
        SocialLink.objects.all().delete()
        Skill.objects.all().delete()
        Experience.objects.all().delete()
        Project.objects.all().delete()
        Education.objects.all().delete()
        Certificate.objects.all().delete()

    # Profile
    if not Profile.objects.filter(is_active=True).exists():
        Profile.objects.create(**DEFAULT_PROFILE)

    # Social Links
    if not SocialLink.objects.exists():
        for s in DEFAULT_SOCIAL_LINKS:
            SocialLink.objects.create(**s)

    # Skills
    if not Skill.objects.exists():
        for sk in DEFAULT_SKILLS:
            Skill.objects.create(**sk)

    # Experiences
    if not Experience.objects.exists():
        for ex in DEFAULT_EXPERIENCES:
            Experience.objects.create(**ex)

    # Projects
    if not Project.objects.exists():
        for pr in DEFAULT_PROJECTS:
            pr_data = dict(pr)
            if "slug" not in pr_data:
                from django.utils.text import slugify
                pr_data["slug"] = slugify(pr_data["title"])
            Project.objects.create(**pr_data)

    # Education
    if not Education.objects.exists():
        for ed in DEFAULT_EDUCATION:
            Education.objects.create(**ed)

    # Certificates
    if not Certificate.objects.exists():
        for ct in DEFAULT_CERTIFICATES:
            Certificate.objects.create(**ct)

