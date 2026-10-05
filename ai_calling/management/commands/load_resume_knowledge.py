from django.core.management.base import BaseCommand
from ai_calling.models import ResumeKnowledgeChunk
from ai_calling.rag_service import generate_embedding


VERIFIED_RESUME_CHUNKS = [
    {
        "chunk_id": "profile_personal",
        "category": "Profile",
        "title": "Personal Details & Contact Summary",
        "content": (
            "Name: Daniel John Britto A.J\n"
            "Location: Kumbakonam, Tamil Nadu, India\n"
            "Email: danieljohnbrittoaj@gmail.com\n"
            "Phone: 9345655206 (+91 9345655206)\n"
            "Role: Software Developer / Python Backend Engineer\n"
            "Profile Summary: Dedicated Python and backend developer with hands-on experience in building "
            "and maintaining Flask and Django backend services, RESTful API integrations, SQL databases (PostgreSQL, MySQL), "
            "and debugging applications."
        ),
    },
    {
        "chunk_id": "edu_bachelor",
        "category": "Education",
        "title": "Bachelor of Engineering in Computer Science and Engineering",
        "content": (
            "Degree: Bachelor of Engineering (B.E.) in Computer Science and Engineering\n"
            "Institution: Madha Institute of Engineering and Technology, Chennai\n"
            "Duration: 2021 – 2025\n"
            "Academic Performance: 76.6%\n"
            "Key Focus: Computer Science fundamentals, Software Engineering, Object-Oriented Programming, "
            "Database Systems, Web Technologies, Data Structures and Algorithms."
        ),
    },
    {
        "chunk_id": "edu_schooling",
        "category": "Education",
        "title": "Secondary & Higher Secondary Education",
        "content": (
            "Higher Secondary Certificate (HSC):\n"
            "- Score: 81%\n"
            "- Year of Completion: 2021\n"
            "\n"
            "Secondary School Leaving Certificate (SSLC):\n"
            "- Score: 77.4%\n"
            "- Year of Completion: 2019"
        ),
    },
    {
        "chunk_id": "exp_levantare",
        "category": "Experience",
        "title": "Current Professional Experience - Levantare Technology",
        "content": (
            "Company: Levantare Technology\n"
            "Role: Backend / Software Developer\n"
            "Duration: January 2026 – Present\n"
            "Work Type: Current Professional Experience\n"
            "Core Responsibilities and Achievements:\n"
            "• Developing and maintaining backend services using Flask.\n"
            "• Working on robust REST API integrations across services.\n"
            "• Fixing user interface (UI) issues in Angular.\n"
            "• Debugging browser console errors and inspecting backend server logs.\n"
            "• Investigating and diagnosing network and API latency/connectivity issues.\n"
            "• Validating data integrity using PostgreSQL and pgAdmin.\n"
            "• Collaborating closely with cross-functional team members to improve application reliability.\n"
            "• Supporting proactive bug fixes and continuous application improvements."
        ),
    },
    {
        "chunk_id": "training_besant",
        "category": "Training",
        "title": "Trainee Experience - Besant Technologies",
        "content": (
            "Company / Training Institute: Besant Technologies\n"
            "Role: Trainee\n"
            "Duration: November 2024 – April 2025\n"
            "Training Program Focus:\n"
            "• Intensive training in Python programming and Object-Oriented Programming (OOP).\n"
            "• SQL database design, queries, and integration using MySQL Workbench.\n"
            "• Full-stack web development principles and CRUD application architecture.\n"
            "• Version control workflows using Git and GitHub.\n"
            "• Development best practices using Visual Studio Code (VS Code).\n"
            "• Hands-on practical project exercises and database-driven application development."
        ),
    },
    {
        "chunk_id": "skills_programming_python",
        "category": "Skills",
        "title": "Programming Languages & Core Python Capabilities",
        "content": (
            "Programming Languages:\n"
            "• Python (Primary strength and language of expertise)\n"
            "• C# (Foundational / basic knowledge)\n"
            "\n"
            "Python Competencies:\n"
            "• Object-Oriented Programming (OOP) paradigms (inheritance, encapsulation, polymorphism)\n"
            "• File handling and I/O operations\n"
            "• Exception handling and resilient error workflows\n"
            "• Data structures (Lists, Dictionaries, Sets, Tuples, Heaps)\n"
            "• Clean code, modular structuring, and scripting"
        ),
    },
    {
        "chunk_id": "skills_backend_web",
        "category": "Skills",
        "title": "Backend Frameworks & Web Development Skills",
        "content": (
            "Backend Frameworks & Technologies:\n"
            "• Flask (Active professional experience at Levantare Technology for backend microservices and APIs)\n"
            "• Django (Extensive project experience building scalable apps, ORM, authentication, and REST endpoints)\n"
            "• Node.js (Basic knowledge)\n"
            "• ASP.NET (Basic knowledge)\n"
            "\n"
            "Frontend Technologies:\n"
            "• HTML & HTML5\n"
            "• CSS & CSS3\n"
            "• JavaScript\n"
            "• Angular (Basics / professional bug fixing experience)\n"
            "• React (Basic knowledge)"
        ),
    },
    {
        "chunk_id": "skills_databases_tools",
        "category": "Skills",
        "title": "Databases, Tools & Additional Capabilities",
        "content": (
            "Databases:\n"
            "• MySQL (Strong practical experience with CRUD and schemas)\n"
            "• PostgreSQL (Professional experience with database validation and queries)\n"
            "• NoSQL (Basic foundational understanding)\n"
            "\n"
            "Developer Tools:\n"
            "• Git & GitHub for version control and collaborative workflows\n"
            "• Postman for REST API testing and endpoint validation\n"
            "• VS Code (Visual Studio Code)\n"
            "• pgAdmin for PostgreSQL management\n"
            "• MySQL Workbench\n"
            "\n"
            "Additional Technical Areas:\n"
            "• PyQt5 (Basics of desktop GUI development)\n"
            "• API Integration (RESTful services)\n"
            "• CRUD development\n"
            "• Software debugging (backend logs, browser console, network requests)"
        ),
    },
    {
        "chunk_id": "project_phishing_detection",
        "category": "Projects",
        "title": "Project: Phishing Detection System",
        "content": (
            "Project: Phishing Detection System\n"
            "Domain: Machine Learning & Cybersecurity\n"
            "Technologies: Python, XGBoost machine learning algorithm, Flask, Streamlit\n"
            "Description: Developed an intelligent machine learning cybersecurity system utilizing the XGBoost algorithm "
            "to analyze and identify fraudulent phishing URLs and websites. Designed deployment pipelines with Flask "
            "and interactive web interfaces using Streamlit.\n"
            "Note on Accuracy: The model accuracy is a placeholder in Daniel's resume; Daniel does not claim an unverified accuracy figure."
        ),
    },
    {
        "chunk_id": "project_blockchain_evoting",
        "category": "Projects",
        "title": "Project: Ethereum Blockchain-Based E-Voting System",
        "content": (
            "Project: Ethereum Blockchain-Based E-Voting System with Face Recognition\n"
            "Technologies: Ethereum Blockchain, OpenCV, Face Recognition, Web3.js, IPFS, React\n"
            "Description: Built a secure, decentralized digital voting platform ensuring election integrity and anonymity. "
            "Integrated real-time biometric face recognition using OpenCV for voter identity authentication before ballot access. "
            "Utilized Ethereum smart contracts and Web3.js for immutable ballot casting, and IPFS for decentralized data storage."
        ),
    },
    {
        "chunk_id": "project_weather_aspnet",
        "category": "Projects",
        "title": "Project: ASP.NET Weather Application",
        "content": (
            "Project: ASP.NET Weather Application\n"
            "Technologies: C#, ASP.NET, OpenWeather API, REST API integration\n"
            "Description: Developed a dynamic weather forecasting web application utilizing C# and ASP.NET. "
            "Integrated the third-party OpenWeather API to retrieve and display live weather conditions, temperature, "
            "and forecast data based on user input."
        ),
    },
    {
        "chunk_id": "project_inventory_mgmt",
        "category": "Projects",
        "title": "Project: Inventory Management System",
        "content": (
            "Project: Inventory Management System\n"
            "Technologies: Python / Web, MySQL Database\n"
            "Description: Developed an inventory and stock management database application using MySQL. "
            "Implemented schemas and queries for product tracking, stock level updates, categories, and inventory logs."
        ),
    },
    {
        "chunk_id": "project_school_mgmt",
        "category": "Projects",
        "title": "Project: School Management System",
        "content": (
            "Project: School Management System\n"
            "Technologies: Python / Web, MySQL Database\n"
            "Description: Created an academic management database solution using MySQL for managing student records, "
            "courses, teacher assignments, and academic administration workflows."
        ),
    },
    {
        "chunk_id": "project_django_todo",
        "category": "Projects",
        "title": "Project: Django To-Do Application",
        "content": (
            "Project: Django To-Do Application\n"
            "Technologies: Python, Django Framework, SQLite/SQL\n"
            "Description: Developed a full-featured task and to-do application implementing clean Create, Read, Update, "
            "and Delete (CRUD) operations, task status toggling, and clean responsive templates."
        ),
    },
    {
        "chunk_id": "project_employee_mgmt",
        "category": "Projects",
        "title": "Project: Python OOP Employee Management System",
        "content": (
            "Project: Python OOP Employee Management System\n"
            "Technologies: Python, Object-Oriented Programming (OOP)\n"
            "Description: Built an employee management software application showcasing core Python OOP concepts "
            "including class inheritance, encapsulation of employee records, salary calculations, and department management."
        ),
    },
    {
        "chunk_id": "project_task_priority_manager",
        "category": "Projects",
        "title": "Project: Task Priority Manager",
        "content": (
            "Project: Task Priority Manager\n"
            "Technologies: Python, Lists, Dictionaries, Heaps (heapq / Priority Queues)\n"
            "Description: Engineered an algorithmic task priority scheduling tool in Python utilizing min-heap/max-heap "
            "priority queue data structures to efficiently organize, rank, and retrieve high-priority tasks in optimal time."
        ),
    },
    {
        "chunk_id": "certifications_activities",
        "category": "Certifications",
        "title": "Certifications, Workshops & Programs",
        "content": (
            "Certifications & Professional Development:\n"
            "• Python Institute CPPA (Certified PCEP / Associate level Python training)\n"
            "• C Training Certification\n"
            "• Connect with Work Program\n"
            "• Ethical Hacking Workshop, KSRIET, October 2023"
        ),
    },
    {
        "chunk_id": "contact_and_career",
        "category": "Contact",
        "title": "Contact Information & Career Interests",
        "content": (
            "Contact Details:\n"
            "• Email: danieljohnbrittoaj@gmail.com\n"
            "• Phone: 9345655206 (+91 9345655206)\n"
            "• Location: Kumbakonam, Tamil Nadu, India\n"
            "• Career Interests: Python Backend Developer, Django & Flask API engineer, Software Engineering roles.\n"
            "• Collaboration: Open to software development opportunities, backend architecture challenges, "
            "and impactful engineering roles."
        ),
    },
]


class Command(BaseCommand):
    help = "Loads and embeds verified resume and portfolio knowledge for Daniel John Britto's AI Assistant"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force re-generation of embeddings even if already cached in database",
        )

    def handle(self, *args, **options):
        force_reembed = options.get("force", False)
        self.stdout.write(self.style.NOTICE("Initializing Daniel's Verified Resume Knowledge Base..."))

        total = len(VERIFIED_RESUME_CHUNKS)
        created_count = 0
        updated_count = 0
        embedded_count = 0

        for idx, item in enumerate(VERIFIED_RESUME_CHUNKS, 1):
            chunk_id = item["chunk_id"]
            category = item["category"]
            title = item["title"]
            content = item["content"]

            chunk, created = ResumeKnowledgeChunk.objects.get_or_create(
                chunk_id=chunk_id,
                defaults={
                    "category": category,
                    "title": title,
                    "content": content,
                    "is_active": True,
                }
            )

            needs_embedding = force_reembed or not chunk.embedding or len(chunk.embedding) == 0

            if not created:
                # Update content if changed
                if chunk.content != content or chunk.title != title or chunk.category != category:
                    chunk.content = content
                    chunk.title = title
                    chunk.category = category
                    needs_embedding = True
                    updated_count += 1
            else:
                created_count += 1

            if needs_embedding:
                self.stdout.write(f"[{idx}/{total}] Embedding ({category}): {title}...")
                text_to_embed = f"{title}\n{content}"
                emb = generate_embedding(text_to_embed)
                if emb:
                    chunk.embedding = emb
                    embedded_count += 1
                    self.stdout.write(self.style.SUCCESS(f"  -> Generated {len(emb)}-dim embedding."))
                else:
                    self.stdout.write(self.style.WARNING("  -> Embedding generation skipped/failed; keyword search will still operate."))

            chunk.is_active = True
            chunk.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSuccessfully populated knowledge base! "
                f"Total chunks: {total} (Created: {created_count}, Updated: {updated_count}, Embedded: {embedded_count})"
            )
        )
