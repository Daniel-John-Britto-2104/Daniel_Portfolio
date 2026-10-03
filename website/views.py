from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.views.decorators.http import require_POST
from .models import (
    Profile,
    SocialLink,
    Skill,
    Experience,
    Project,
    Education,
    Certificate,
    ContactMessage,
)


def home(request):
    profile = Profile.objects.filter(is_active=True).first()
    if not profile:
        # Fallback default profile if table is empty
        profile = Profile(
            full_name="Daniel John Britto",
            title="Python Developer | Django & Full Stack Developer",
            headline="Python Developer at Thaagam Foundation | Specializing in Django Backend & Angular Full Stack Development",
            bio="Passionate Python Developer currently working at Thaagam Foundation with 6 months of hands-on software development experience. Experienced in building robust Django backend applications, RESTful APIs, and full stack web solutions using Angular and Python.",
            years_of_experience=1,
            projects_completed=8,
            location="Chennai, India",
            email="danielamalraj309@gmail.com",
            phone="+91 98765 43210",
        )

    social_links = SocialLink.objects.all()
    skills = Skill.objects.all()
    
    # Group skills by category
    skills_by_category = {
        "Languages": [s for s in skills if s.category == "Languages"],
        "Frameworks": [s for s in skills if s.category == "Frameworks"],
        "Databases": [s for s in skills if s.category == "Databases"],
        "Tools": [s for s in skills if s.category == "Tools"],
    }

    experiences = Experience.objects.all()
    projects = Project.objects.all()
    education_list = Education.objects.all()
    certificates = Certificate.objects.all()

    context = {
        "profile": profile,
        "social_links": social_links,
        "skills": skills,
        "skills_by_category": skills_by_category,
        "experiences": experiences,
        "projects": projects,
        "education_list": education_list,
        "certificates": certificates,
    }
    return render(request, "home.html", context)


@require_POST
def contact_submit(request):
    name = request.POST.get("name", "").strip()
    email = request.POST.get("email", "").strip()
    subject = request.POST.get("subject", "").strip()
    message_text = request.POST.get("message", "").strip()

    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

    if not name or not email or not message_text:
        error_msg = "Please fill in all required fields."
        if is_ajax:
            return JsonResponse({"success": False, "message": error_msg}, status=400)
        messages.error(request, error_msg)
        return redirect("home")

    ContactMessage.objects.create(
        name=name,
        email=email,
        subject=subject or "General Inquiry",
        message=message_text,
    )

    success_msg = f"Thank you, {name}! Your message has been sent successfully. I will get back to you soon."
    
    if is_ajax:
        return JsonResponse({"success": True, "message": success_msg})

    messages.success(request, success_msg)
    return redirect("home")


def robots_txt(request):
    content = """User-agent: *
Allow: /
Disallow: /admin/
Sitemap: http://127.0.0.1:8000/sitemap.xml
"""
    return HttpResponse(content, content_type="text/plain")


def sitemap_xml(request):
    content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
   <url>
      <loc>http://127.0.0.1:8000/</loc>
      <changefreq>weekly</changefreq>
      <priority>1.0</priority>
   </url>
</urlset>
"""
    return HttpResponse(content, content_type="application/xml")