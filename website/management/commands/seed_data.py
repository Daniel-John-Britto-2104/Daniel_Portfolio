from django.core.management.base import BaseCommand
from website.models import (
    Profile,
    SocialLink,
    Skill,
    Experience,
    Project,
    Education,
    Certificate,
)


class Command(BaseCommand):
    help = "Seed database with Daniel John Britto's updated portfolio and resume data"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding portfolio data..."))

        # Profile
        Profile.objects.all().delete()
        profile = Profile.objects.create(
            full_name="Daniel John Britto",
            title="Python Developer | Django & Full Stack Developer",
            headline="Python Developer at Thaagam Foundation | Specializing in Django Backend & Angular Full Stack Development",
            bio="Passionate Python Developer currently working at Thaagam Foundation with 6 months of hands-on software development experience. Experienced in building robust Django backend applications, RESTful APIs, and full stack web solutions using Angular and Python.",
            years_of_experience=1,
            projects_completed=8,
            location="Chennai, India",
            email="danieljohnbrittoaj@gmail.com",
            phone="+91 98765 43210",
            resume_url="#",
            profile_image_url="/static/images/profile.svg",
            is_active=True,
        )
        self.stdout.write(self.style.SUCCESS("[OK] Profile created."))

        # Social Links
        SocialLink.objects.all().delete()
        socials = [
            {"platform": "GitHub", "url": "https://github.com/danieljohnbritto21", "icon_name": "github", "order": 1},
            {"platform": "LinkedIn", "url": "https://www.linkedin.com/in/daniel-john-britto-21-dev", "icon_name": "linkedin", "order": 2},
            {"platform": "Email", "url": "mailto:danieljohnbrittoaj@gmail.com", "icon_name": "mail", "order": 3},
        ]
        for s in socials:
            SocialLink.objects.create(**s)
        self.stdout.write(self.style.SUCCESS("[OK] Social links created."))

        # Skills
        Skill.objects.all().delete()
        skills = [
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
        for sk in skills:
            Skill.objects.create(**sk)
        self.stdout.write(self.style.SUCCESS("[OK] Skills created."))

        # Experiences
        Experience.objects.all().delete()
        exps = [
            {
                "company": "Thaagam Foundation",
                "role": "Python Developer",
                "location": "Chennai, India",
                "is_current": True,
                "start_date": "Recent",
                "end_date": "Present",
                "description": "Serving as a Python Developer building backend architectures, data management tools, and REST API services.",
                "responsibilities_raw": "Developing core Python backend applications and managing database workflows\nBuilding and integrating scalable REST API endpoints\nCollaborating on technical feature rollouts and optimizing web system performance",
                "tech_stack": "Python, Django, PostgreSQL, REST APIs, Git",
                "order": 1,
            },
            {
                "company": "Full Stack Developer Internship",
                "role": "Full Stack Developer Intern (Angular & Django)",
                "location": "Chennai, India",
                "is_current": False,
                "start_date": "2024",
                "end_date": "2024",
                "description": "Completed an intensive Full Stack Developer internship specializing in Angular frontend and Django backend engineering.",
                "responsibilities_raw": "Developed responsive user interface components using Angular framework\nEngineered Django REST Framework backend APIs and SQL database models\nIntegrated cross-origin requests, JWT authentication, and CRUD functionalities\nCollaborated using Git/GitHub for version control and code iterations",
                "tech_stack": "Angular, Django, Python, TypeScript, SQL, REST APIs, GitHub",
                "order": 2,
            },
        ]
        for e in exps:
            Experience.objects.create(**e)
        self.stdout.write(self.style.SUCCESS("[OK] Experiences created."))

        # Projects
        Project.objects.all().delete()
        projects = [
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
        for p in projects:
            Project.objects.create(**p)
        self.stdout.write(self.style.SUCCESS("[OK] Projects created."))

        # Education
        Education.objects.all().delete()
        edu = [
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
        for ed in edu:
            Education.objects.create(**ed)
        self.stdout.write(self.style.SUCCESS("[OK] Education records created."))

        # Certificates
        Certificate.objects.all().delete()
        certs = [
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
        for c in certs:
            Certificate.objects.create(**c)
        self.stdout.write(self.style.SUCCESS("[OK] Certificates created."))

        self.stdout.write(self.style.SUCCESS("Successfully seeded all updated portfolio database tables!"))
